import sqlite3
from werkzeug.security import generate_password_hash

# === CONFIG ===
db_path = 'sql/washit.db'
admin_name = 'Taha'
admin_email = 'taha@gmail.com'
admin_password_raw = '123'

# === HASH PASSWORD ===
hashed_pw = generate_password_hash(admin_password_raw)

# === INSERT INTO DATABASE ===
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (admin_name, admin_email, hashed_pw, 'admin'))
    conn.commit()
    print(f"✅ Admin user '{admin_email}' added successfully!")
except sqlite3.IntegrityError:
    print(f"⚠ Email '{admin_email}' is already registered.")
finally:
    conn.close()
