import sqlite3

# ================= DATABASE SETUP SCRIPT =================

# Dit script maakt de SQLite database aan (of opent ze als ze al bestaat)
# en zorgt ervoor dat alle nodige tabellen correct aanwezig zijn.

# SQLite wordt gebruikt omdat:
# - het lichtgewicht is
# - geen aparte server nodig heeft
# - perfect is voor kleine Flask-projecten

# Maak verbinding met de database (bestand atletiek.db)
conn = sqlite3.connect("atletiek.db")

# Cursor object om SQL-commando’s uit te voeren
cursor = conn.cursor()


# ================= USERS TABEL =================

# Deze tabel bevat alle gebruikers van de applicatie.

# Structuur:
# - id: unieke identifier (automatisch oplopend)
# - username: naam van de gebruiker
# - password: wachtwoord (in deze versie niet gehasht -> enkel voor demo)

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")

# ================= PERFORMANCES TABEL =================

# Deze tabel bevat alle sportprestaties van gebruikers.

# Elke prestatie bevat:
# - user_id: link naar gebruiker (relatie met users tabel)
# - name: naam van de atleet
# - discipline: bv. 100m, 200m, 400m, 800m
# - result: prestatie (tijd of afstand)
# - date: datum van prestatie
# - wind_speed: windsnelheid (enkel relevant voor sprintnummers)
# - wind_direction: richting van de wind (meewind/tegenwind)

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

# ================= DATABASE OPSLAAN =================

# commit() zorgt ervoor dat alle wijzigingen effectief
# worden opgeslagen in het databasebestand.
conn.commit()

# sluit de verbinding om geheugen vrij te maken
conn.close()

# bevestiging in console dat setup succesvol is uitgevoerd
print("Database klaar!")