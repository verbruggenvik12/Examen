-- ================= USERS TABEL =================

-- Deze tabel bevat alle geregistreerde gebruikers van de applicatie.

-- Elke gebruiker heeft:
-- - een uniek ID (primary key)
-- - een gebruikersnaam
-- - een wachtwoord

-- NOT NULL:
-- zorgt ervoor dat username en password verplicht ingevuld moeten zijn

-- UNIQUE:
-- zorgt ervoor dat geen twee gebruikers dezelfde username kunnen hebben
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);


-- ================= PERFORMANCES TABEL =================

-- Deze tabel slaat alle sportprestaties op van gebruikers.

-- Elke rij stelt één prestatie voor (bv. een 100m sprint of 200m tijd)

CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Koppeling naar gebruiker
    -- Verwijst naar users.id zodat elke prestatie bij een gebruiker hoort
    user_id INTEGER,

    -- Naam van de atleet (kan gelijk zijn aan username of apart ingevoerd)
    name TEXT,

    -- Discipline(bv. 100m, 200m, 400m, 800m)
    discipline TEXT,

    -- Resultaat van de prestatie
    -- REAL = numerieke waarde
    result REAL,

    -- Datum 
    date TEXT,

    -- Windsnelheid (100m en 200m)
    wind_speed REAL,

    -- Windrichting:
    -- "meewind" of "tegenwind"
    wind_direction TEXT,

    -- Foreign key constraint:
    -- zorgt ervoor dat user_id altijd moet bestaan in users tabel
    FOREIGN KEY(user_id) REFERENCES users(id)
);