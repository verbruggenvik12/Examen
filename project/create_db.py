import sqlite3

# Maak verbinding met de SQLite database voor atletiekgegevens
conn = sqlite3.connect("atletiek.db")
cursor = conn.cursor()

# Maak tabel voor gebruikers als deze nog niet bestaat
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")

# Maak tabel voor prestaties met verwijzing naar gebruikers
# Inclusief windmeting voor 100m en 200m
cursor.execute("""
CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    discipline TEXT,
    result REAL,
    date TEXT,
    wind_speed REAL,
    wind_direction TEXT
)
""")

# Sla de wijzigingen op en sluit de databaseverbinding
conn.commit()
conn.close()

print("Database klaar!")
