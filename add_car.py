import sqlite3

DATABASE = 'sql/washit.db'

# List of (name, rate) tuples to insert
car_categories = [
    ('600cc', 250),
    ('800cc', 320),
    ('1000cc', 350),
    ('1200cc', 400),
    ('1400cc', 430),
    ('1500cc', 450),
    ('1600cc', 500),
    ('1800cc', 550),
    ('2000cc', 600),
    ('2200cc', 630),
    ('2500cc', 750),
    ('2600cc', 800),
    ('2700cc', 900),
]

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

for name, rate in car_categories:
    cursor.execute("INSERT INTO car_categories (name, rate) VALUES (?, ?)", (name, rate))
    print(f"Added {name} with rate {rate}")

conn.commit()
conn.close()
print("All car categories inserted successfully.")
