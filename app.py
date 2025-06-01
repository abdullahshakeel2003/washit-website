from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sql', 'washit.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('signin'))

@app.route('/dashboard')
def dashboard():
    with get_db() as conn:
        categories = conn.execute('SELECT * FROM car_categories').fetchall()
    return render_template('dashboard.html', categories=categories)

@app.route('/book/<int:category_id>', methods=['POST'])
@login_required
def book(category_id):
    user_id = session['user_id']
    date = request.form['date']  # yyyy-mm-dd
    time = request.form['time']  # hh:mm

    # Combine date + time into a single datetime string (optional)
    start_time = f"{date} {time}:00"

    with get_db() as conn:
        conn.execute('''
            INSERT INTO appointments (user_id, category_id, status, start_time)
            VALUES (?, ?, ?, ?)
        ''', (user_id, category_id, 'pending', start_time))
        conn.commit()

    flash('Appointment booked successfully!', 'success')
    return redirect(url_for('appointments'))


@app.route('/appointments')
@login_required
def appointments():
    user_id = session['user_id']

    def split_datetime(row):
        # row['start_time'] is a string like 'YYYY-MM-DD HH:MM:SS'
        dt = row['start_time']
        if dt:
            date_part, time_part = dt.split(' ')
            time_part = time_part[:5]  # get HH:MM only
        else:
            date_part, time_part = None, None
        
        # Convert sqlite3.Row to dict to add date/time easily
        appt = dict(row)
        appt['date'] = date_part
        appt['time'] = time_part
        return appt

    with get_db() as conn:
        pending_rows = conn.execute("""
            SELECT a.*, c.name AS car_name, c.rate
            FROM appointments a
            JOIN car_categories c ON a.category_id = c.id
            WHERE a.user_id=? AND a.status='pending'
        """, (user_id,)).fetchall()

        active_rows = conn.execute("""
            SELECT a.*, c.name AS car_name, c.rate
            FROM appointments a
            JOIN car_categories c ON a.category_id = c.id
            WHERE a.user_id=? AND a.status='active'
        """, (user_id,)).fetchall()

        history_rows = conn.execute("""
            SELECT a.*, c.name AS car_name, c.rate
            FROM appointments a
            JOIN car_categories c ON a.category_id = c.id
            WHERE a.user_id=? AND a.status='completed'
        """, (user_id,)).fetchall()

    # Map and add date/time fields
    pending = [split_datetime(row) for row in pending_rows]
    active = [split_datetime(row) for row in active_rows]
    history = [split_datetime(row) for row in history_rows]

    return render_template('appointments.html', pending=pending, active=active, history=history)

@app.route('/cancel/<int:appt_id>', methods=['POST'])
def cancel_appointment(appt_id):
    conn = get_db()
    cur = conn.cursor()

    # Check if appointment exists and is active
    cur.execute("SELECT * FROM appointments WHERE id=? AND status='active'", (appt_id,))
    appt = cur.fetchone()

    if appt:
        cur.execute("UPDATE appointments SET status='canceled' WHERE id=?", (appt_id,))
        conn.commit()
        flash('Appointment canceled successfully.', 'success')
    else:
        flash('Appointment not found or already canceled.', 'danger')

    conn.close()
    return redirect(url_for('appointments'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_pw))
            conn.commit()
            flash('Account created! Please sign in.', 'success')
        except:
            flash('Email already registered.', 'danger')
        conn.close()
        return redirect(url_for('signin'))
    
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('signin'))

    return render_template('signin.html', body_class='signin-page')



@app.route('/guest', methods=['POST'])
def guest():
    session['user_id'] = None
    session['user_name'] = 'Guest'
    flash('Continuing as guest.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('signin'))

@app.route('/admin')
@login_required
def admin_panel():
    with get_db() as conn:
        all_appointments = conn.execute("""
    SELECT a.id, u.name AS user_name, c.name AS category_name, c.rate, a.status, a.start_time
    FROM appointments a
    JOIN users u ON a.user_id = u.id
    JOIN car_categories c ON a.category_id = c.id
        """).fetchall()

    return render_template('admin_panel.html', appointments=all_appointments)

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    with get_db() as conn:
        conn.execute("DELETE FROM appointments WHERE id=?", (appointment_id,))
        conn.commit()
    return redirect(url_for('admin_panel'))


@app.route('/update_status/<int:appointment_id>/<status>')
@login_required
def update_status(appointment_id, status):
    with get_db() as conn:
        if status == 'active':
            start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute("UPDATE appointments SET status=?, start_time=? WHERE id=?", (status, start_time, appointment_id))
        else:
            conn.execute("UPDATE appointments SET status=? WHERE id=?", (status, appointment_id))
        conn.commit()
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    app.run(debug=True)
