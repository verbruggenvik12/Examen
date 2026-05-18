import sqlite3

# maak verbinding met database (maakt automatisch bestand aan)
conn = sqlite3.connect("atletiek.db")

cursor = conn.cursor()

# maak tabel
cursor.execute("""
CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    discipline TEXT,
    result REAL,
    date TEXT
)
""")

conn.commit()
conn.close()

print("Database en tabel gemaakt!")