-- Tabel voor geregistreerde gebruikers
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- Tabel voor prestaties gekoppeld aan een gebruiker
-- Inclusief windmeting voor 100m en 200m
CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    discipline TEXT,
    result REAL,
    date TEXT,
    wind_speed REAL,
    wind_direction TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
