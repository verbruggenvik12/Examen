import re
from datetime import datetime
from cs50 import SQL
from flask import Flask, render_template, request, redirect, session
import sqlite3

# ================= FLASK APP INITIALISATIE =================

app = Flask(__name__)

# Secret key is nodig voor sessiebeheer (login, admin-status, user_id)
app.secret_key = "geheim"


# ================= TEMPLATE FILTER =================

@app.template_filter('format_date')
def format_date(value):
    """
    Custom Jinja filter om datums netjes te formatteren.

    Doel:
    - verschillende databank-formaten ondersteunen
    - altijd output tonen als dd/mm/yyyy
    """

    # Als er geen waarde is -> lege string teruggeven
    if not value:
        return ""

    # Als het al een datetime object is
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    # Zet input om naar string en verwijder spaties
    text = str(value).strip()

    # Mogelijke formaten die uit database kunnen komen
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue

    # Als geen formaat matcht: toon originele tekst
    return text


# ================= DATABASE CONNECTIE =================

# cs50 SQL wrapper rond SQLite database
db = SQL("sqlite:///atletiek.db")


# ================= CONSTANTEN =================

# Alle beschikbare disciplines in de app
DISCIPLINES = ["100m", "200m", "400m", "800m"]

# Disciplines waarbij wind een rol speelt
WIND_DISCIPLINES = ["100m", "200m"]


# ================= DATABASE STRUCTUUR CHECK =================

def ensure_wind_columns():
    """
    Controleert of de tabel performances de juiste kolommen heeft.

    Als de app op een nieuwe database draait,
    worden ontbrekende kolommen automatisch toegevoegd.
    """

    conn = sqlite3.connect("atletiek.db")
    cursor = conn.cursor()

    # Haal tabelstructuur op
    cursor.execute("PRAGMA table_info(performances)")
    columns = [row[1] for row in cursor.fetchall()]

    # Voeg wind_speed toe indien niet aanwezig
    if "wind_speed" not in columns:
        cursor.execute("ALTER TABLE performances ADD COLUMN wind_speed REAL")

    # Voeg wind_direction toe indien niet aanwezig
    if "wind_direction" not in columns:
        cursor.execute("ALTER TABLE performances ADD COLUMN wind_direction TEXT")

    conn.commit()
    conn.close()


# Voer check meteen uit bij opstarten
ensure_wind_columns()


# ================= RESULT PARSING =================

def parse_result_seconds(result):
    """
    Zet verschillende result-formaten om naar seconden.

    Ondersteunde formaten:
    - float (bv 12.34)
    - mm:ss:hh
    - ss:hh
    - losse getallen

    Wordt gebruikt om correct te sorteren (fastest/slowest)
    """

    # Geen resultaat -> oneindig (achteraan sorteren)
    if result is None:
        return float('inf')

    try:
        return float(result)
    except Exception:
        pass

    text = str(result)

    # Zoek alle cijfers in string
    parts = re.findall(r"\d+", text)

    if not parts:
        return float('inf')

    # mm:ss:hh
    if len(parts) == 3:
        minutes, seconds, hundredths = parts
        return int(minutes) * 60 + int(seconds) + int(hundredths) / 100.0

    # ss:hh
    if len(parts) == 2:
        seconds, hundredths = parts
        return int(seconds) + int(hundredths) / 100.0

    # enkel getal
    if len(parts) == 1:
        return float(parts[0])

    try:
        return float(parts[0])
    except Exception:
        return float('inf')


# ================= HELPER FUNCTIONS =================

def annotate_wind(rows):
    """
    Verrijkt database-rows met extra informatie:

    - invalid_wind (voor rode waarschuwing in UI)
    - wind_display (mooie string voor UI)
    """

    for row in rows:

        # standaardwaarden
        row["invalid_wind"] = False
        row["wind_display"] = ""

        wind_speed = row.get("wind_speed")
        wind_direction = row.get("wind_direction")

        # geen winddata -> skip
        if wind_speed is None or wind_speed == "":
            continue

        try:
            # omzetting naar float (ook komma's ondersteunen)
            wind_speed = float(str(wind_speed).replace(',', '.'))

            # richting normaliseren (case-insensitive)
            direction_clean = str(wind_direction).strip().lower()

            # teken bepalen voor display
            if direction_clean == "meewind":
                sign = "+"
            else:
                sign = "-"

            # mooie weergave voor frontend
            row["wind_display"] = f"{sign}{wind_speed:.1f} m/s"

            # INVALID LOGICA:
            # alleen meewind + >= 2.0 m/s is ongeldig
            # tegenwind wordt nooit ongeldig
            if direction_clean == "meewind" and wind_speed >= 2.0:
                row["invalid_wind"] = True

        except:
            # bij fout gewoon leeg laten
            row["wind_display"] = ""

    return rows


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    # POST = gebruiker probeert in te loggen
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # HARD-CODED admin login
        if username == "Trainer" and password == "trainer123":
            session["admin"] = True
            return redirect("/admin")

        # gewone user check in database
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            username, password
        )

        # correcte login
        if len(user) == 1:
            session["user_id"] = user[0]["id"]
            return redirect("/")
        else:
            # foutmelding pagina
            return render_template("error.html", message="Foute login")

    # GET = toon loginpagina
    return render_template("login.html")


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    # nieuwe gebruiker aanmaken
    if request.method == "POST":

        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            request.form.get("username"),
            request.form.get("password")
        )

        return redirect("/login")

    return render_template("register.html")


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    # sessie volledig leegmaken
    session.clear()
    return redirect("/login")


# ================= HOME =================

@app.route("/")
def index():

    # enkel toegelaten als ingelogd
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "index.html",
        disciplines=DISCIPLINES
    )


# ================= ADD PERFORMANCE =================

@app.route("/add", methods=["POST"])
def add():

    discipline = request.form.get("discipline")
    wind_speed = request.form.get("wind_speed")
    wind_direction = request.form.get("wind_direction")

    # geen wind bij niet-sprint disciplines
    if discipline not in WIND_DISCIPLINES:
        wind_speed = None
        wind_direction = None

    else:
        # lege waarde = None
        if wind_speed == "":
            wind_speed = None

        # richting standaardiseren
        if wind_direction:
            wind_direction = wind_direction.lower()

        if wind_direction not in ["meewind", "tegenwind"]:
            wind_direction = None

    # opslaan in database
    db.execute("""
        INSERT INTO performances
        (user_id, name, discipline, result, date, wind_speed, wind_direction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    session["user_id"],
    request.form.get("name"),
    discipline,
    request.form.get("result"),
    request.form.get("date"),
    wind_speed,
    wind_direction
    )

    return redirect("/performances")


# ================= OVERZICHT PRESTATIES =================

@app.route("/performances")
def performances():

    # admin ziet alles
    if session.get("admin"):
        query = "SELECT * FROM performances"
        params = []

    # user ziet enkel eigen prestaties
    else:
        if "user_id" not in session:
            return redirect("/login")

        query = "SELECT * FROM performances WHERE user_id = ?"
        params = [session["user_id"]]

    discipline = request.args.get("discipline")
    sort = request.args.get("sort")

    # filter op discipline
    if discipline and discipline in DISCIPLINES:
        if "WHERE" in query:
            query += " AND discipline = ?"
        else:
            query += " WHERE discipline = ?"
        params.append(discipline)

    order_options = {
        "recent": "date ASC",
        "oldest": "date DESC"
    }

    # sorting op tijd (complex omdat string -> seconds nodig is)
    if sort in ["fastest", "slowest"]:

        rows = db.execute(query, *params)

        rows = sorted(
            rows,
            key=lambda r: parse_result_seconds(r.get("result")),
            reverse=(sort == "slowest")
        )

    else:
        order_by = order_options.get(sort)

        if order_by:
            query += f" ORDER BY {order_by}"
        else:
            query += " ORDER BY date DESC"

        rows = db.execute(query, *params)

    # wind annotatie voor UI
    rows = annotate_wind(rows)

    return render_template(
        "performances.html",
        performances=rows,
        disciplines=DISCIPLINES,
        selected_discipline=discipline,
        selected_sort=sort
    )


# ================= ADMIN =================

@app.route("/admin")
def admin():

    # alleen admin toegestaan
    if not session.get("admin"):
        return redirect("/login")

    rows = db.execute("""
        SELECT performances.*, users.username
        FROM performances
        JOIN users ON users.id = performances.user_id
    """)

    rows = annotate_wind(rows)

    return render_template(
        "admin.html",
        performances=rows
    )


# ================= DELETE =================

@app.route("/delete", methods=["POST"])
def delete():

    # verwijder prestatie op basis van ID
    db.execute(
        "DELETE FROM performances WHERE id = ?",
        request.form.get("id")
    )

    return redirect("/performances")


# ================= EDIT =================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    # alleen admin mag bewerken
    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":

        discipline = request.form.get("discipline")
        wind_speed = request.form.get("wind_speed")
        wind_direction = request.form.get("wind_direction")

        # zelfde windlogica als add()
        if discipline not in WIND_DISCIPLINES:
            wind_speed = None
            wind_direction = None
        else:
            if wind_speed == "":
                wind_speed = None
            if wind_direction:
                wind_direction = wind_direction.lower()
            if wind_direction not in ["meewind", "tegenwind"]:
                wind_direction = None

        db.execute("""
            UPDATE performances
            SET name = ?, discipline = ?, result = ?, date = ?, wind_speed = ?, wind_direction = ?
            WHERE id = ?
        """,
        request.form.get("name"),
        discipline,
        request.form.get("result"),
        request.form.get("date"),
        wind_speed,
        wind_direction,
        id
        )

        return redirect("/admin")

    # bestaande data ophalen
    p = db.execute(
        "SELECT * FROM performances WHERE id = ?",
        id
    )[0]

    return render_template(
        "edit.html",
        p=p,
        disciplines=DISCIPLINES
    )


# ================= PR PAGINA =================

@app.route("/pr", methods=["GET", "POST"])
def pr():

    # toegang controleren
    if not session.get("admin") and "user_id" not in session:
        return redirect("/login")

    # admin ziet geen eigen PR blok
    if session.get("admin"):
        my_results = []

    else:
        # eigen PR per discipline (min = beste tijd)
        my_results = db.execute("""
            SELECT discipline, MIN(result) as best
            FROM performances
            WHERE user_id = ?
            GROUP BY discipline
        """, session["user_id"])

    search_results = None

    # zoeken naar andere gebruiker
    if request.method == "POST":

        name = request.form.get("name")

        search_results = db.execute("""
            SELECT discipline, MIN(result) as best
            FROM performances
            WHERE name = ? COLLATE NOCASE
            GROUP BY discipline
        """, name)

    return render_template(
        "pr.html",
        my_results=my_results,
        search_results=search_results,
        is_admin=session.get("admin")
    )


# ================= APP START =================

if __name__ == "__main__":
    app.run(debug=True)