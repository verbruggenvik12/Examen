import re
from datetime import datetime
from cs50 import SQL
from flask import Flask, render_template, request, redirect, session
import sqlite3


# =========================================================
# FLASK INITIALISATIE
# =========================================================

app = Flask(__name__)

# Secret key is nodig om sessies te beheren (login, admin, user_id)
app.secret_key = "geheim"


# =========================================================
# TEMPLATE FILTER: DATUM FORMATTEREN
# =========================================================

@app.template_filter('format_date')
def format_date(value):
    """
    Zet verschillende datumformaten om naar dd/mm/yyyy
    zodat alles uniform wordt weergegeven in de frontend.
    """

    # Als er geen datum is → lege string teruggeven
    if not value:
        return ""

    # Als waarde al een datetime object is → direct formatteren
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    # Zet alles om naar string en verwijder spaties
    text = str(value).strip()

    # Verschillende mogelijke input-formaten uit database
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue

    # Als geen format matcht → originele waarde tonen
    return text


# =========================================================
# DATABASE CONNECTIE
# =========================================================

# cs50 SQL wrapper voor SQLite database
db = SQL("sqlite:///atletiek.db")


# =========================================================
# CONSTANTEN
# =========================================================

# Alle disciplines die in de app bestaan
DISCIPLINES = ["100m", "200m", "400m", "800m"]

# Disciplines waarbij wind belangrijk is (sprints)
WIND_DISCIPLINES = ["100m", "200m"]


# =========================================================
# DATABASE STRUCTUUR CHECK
# =========================================================

def ensure_wind_columns():
    """
    Controleert of de database de juiste kolommen heeft.
    Als ze ontbreken → worden ze automatisch toegevoegd.
    """

    conn = sqlite3.connect("atletiek.db")
    cursor = conn.cursor()

    # Haal alle kolommen op uit tabel performances
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


# Voer check uit bij opstarten van app
ensure_wind_columns()


# =========================================================
# RESULT PARSING (voor sortering)
# =========================================================

def parse_result_seconds(result):
    """
    Zet verschillende tijdformaten om naar seconden
    zodat we correct kunnen sorteren (fastest/slowest).
    """

    if result is None:
        return float('inf')

    try:
        return float(result)
    except:
        pass

    parts = re.findall(r"\d+", str(result))

    # mm:ss:hh formaat
    if len(parts) == 3:
        m, s, h = parts
        return int(m) * 60 + int(s) + int(h) / 100

    # ss:hh formaat
    if len(parts) == 2:
        s, h = parts
        return int(s) + int(h) / 100

    # enkel getal
    if len(parts) == 1:
        return float(parts[0])

    return float('inf')


# =========================================================
# WIND LOGICA HELPER
# =========================================================

def annotate_wind(rows):
    """
    Voegt extra informatie toe aan elke row:

    - wind_display (mooie tekst voor UI)
    - invalid_wind (rode waarschuwing bij +2.0 m/s meewind)
    """

    for row in rows:

        row["invalid_wind"] = False
        row["wind_display"] = ""

        wind_speed = row.get("wind_speed")
        wind_direction = row.get("wind_direction")

        # geen winddata → skip
        if wind_speed is None or wind_speed == "":
            continue

        try:
            # ondersteunt komma en punt
            wind_speed = float(str(wind_speed).replace(",", "."))

            direction = str(wind_direction).strip().lower()

            # teken voor display
            sign = "+" if direction == "meewind" else "-"

            row["wind_display"] = f"{sign}{wind_speed:.1f} m/s"

            # ongeldig bij meewind >= 2.0 m/s
            if direction == "meewind" and wind_speed >= 2.0:
                row["invalid_wind"] = True

        except:
            # bij fout niets tonen
            pass

    return rows


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # POST = login poging
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # admin login (hardcoded)
        if username == "Trainer" and password == "trainer123":
            session["admin"] = True
            return redirect("/admin")

        # gewone user login via database
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            username, password
        )

        if len(user) == 1:
            session["user_id"] = user[0]["id"]
            return redirect("/")

        return render_template("error.html", message="Foute login")

    return render_template("login.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    # nieuwe gebruiker opslaan
    if request.method == "POST":
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            request.form.get("username"),
            request.form.get("password")
        )
        return redirect("/login")

    return render_template("register.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    # sessie volledig wissen
    session.clear()
    return redirect("/login")


# =========================================================
# HOMEPAGE
# =========================================================

@app.route("/")
def index():

    # enkel ingelogde gebruikers
    if "user_id" not in session:
        return redirect("/login")

    return render_template("index.html", disciplines=DISCIPLINES)


# =========================================================
# ADD PERFORMANCE
# =========================================================

@app.route("/add", methods=["POST"])
def add():

    # basis input ophalen
    name = request.form.get("name")
    result = request.form.get("result")
    date = request.form.get("date")

    discipline = request.form.get("discipline")
    wind_speed = request.form.get("wind_speed")
    wind_direction = request.form.get("wind_direction")

    # -----------------------------
    # verplichte velden check
    # -----------------------------
    if not name or not result or not date or not wind_speed:
        return render_template("error.html",
                               message="Naam, resultaat, datum en windmeting zijn verplicht.")

    # -----------------------------
    # result validatie (tijd formaat)
    # -----------------------------
    if not re.match(r'^\d{1,2}"\d{2}"\d{2}$', result):
        return render_template("error.html",
                               message="Resultaat moet zo geformateerd zijn: 12\"02\'89 (min\"sec'ms)")

    if len(result) != 8:
        return render_template("error.html",
                               message="Resultaat moet exact 8 tekens zijn.")

    # -----------------------------
    # wind validatie
    # -----------------------------
    if discipline in WIND_DISCIPLINES and not wind_speed:
        return render_template("error.html",
                               message="Wind verplicht voor 100m en 200m.")

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

    # -----------------------------
    # opslaan in database
    # -----------------------------
    db.execute("""
        INSERT INTO performances
        (user_id, name, discipline, result, date, wind_speed, wind_direction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    session["user_id"],
    name,
    discipline,
    result,
    date,
    wind_speed,
    wind_direction
    )

    return redirect("/performances")


# =========================================================
# OVERZICHT PRESTATIES
# =========================================================

@app.route("/performances")
def performances():

    # admin ziet alles
    if session.get("admin"):
        query = "SELECT * FROM performances"
        params = []
    else:
        if "user_id" not in session:
            return redirect("/login")

        query = "SELECT * FROM performances WHERE user_id = ?"
        params = [session["user_id"]]

    discipline = request.args.get("discipline")
    sort = request.args.get("sort")

    # filter op discipline
    if discipline and discipline in DISCIPLINES:
        query += " AND discipline = ?" if "WHERE" in query else " WHERE discipline = ?"
        params.append(discipline)

    # sortering op tijd
    if sort in ["fastest", "slowest"]:
        rows = db.execute(query, *params)
        rows = sorted(rows,
                      key=lambda r: parse_result_seconds(r.get("result")),
                      reverse=(sort == "slowest"))
    else:
        rows = db.execute(query, *params)

    rows = annotate_wind(rows)

    return render_template(
        "performances.html",
        performances=rows,
        disciplines=DISCIPLINES
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect("/login")

    rows = db.execute("""
        SELECT performances.*, users.username
        FROM performances
        JOIN users ON users.id = performances.user_id
    """)

    rows = annotate_wind(rows)

    return render_template("admin.html", performances=rows)


# =========================================================
# DELETE
# =========================================================

@app.route("/delete", methods=["POST"])
def delete():

    # verwijder performance op basis van id
    db.execute("DELETE FROM performances WHERE id = ?",
               request.form.get("id"))

    return redirect("/performances")


# =========================================================
# EDIT PERFORMANCE
# =========================================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":

        name = request.form.get("name")
        result = request.form.get("result")
        date = request.form.get("date")

        discipline = request.form.get("discipline")
        wind_speed = request.form.get("wind_speed")
        wind_direction = request.form.get("wind_direction")

        # result validatie
        if not re.match(r'^\d{1,2}"\d{2}"\d{2}$', result):
            return render_template("error.html",
                                   message="Ongeldig resultaat")

        if len(result) != 8:
            return render_template("error.html",
                                   message="Resultaat moet 8 tekens zijn")

        # wind logica
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
            SET name=?, discipline=?, result=?, date=?, wind_speed=?, wind_direction=?
            WHERE id=?
        """,
        name, discipline, result, date,
        wind_speed, wind_direction, id)

        return redirect("/admin")

    p = db.execute("SELECT * FROM performances WHERE id = ?", id)[0]

    return render_template("edit.html", p=p, disciplines=DISCIPLINES)


# =========================================================
# PR PAGINA
# =========================================================

@app.route("/pr", methods=["GET", "POST"])
def pr():

    if not session.get("admin") and "user_id" not in session:
        return redirect("/login")

    my_results = [] if session.get("admin") else db.execute("""
        SELECT discipline, MIN(result) as best
        FROM performances
        WHERE user_id=?
        GROUP BY discipline
    """, session["user_id"])

    search_results = None

    if request.method == "POST":
        name = request.form.get("name")

        search_results = db.execute("""
            SELECT discipline, MIN(result) as best
            FROM performances
            WHERE name=? COLLATE NOCASE
            GROUP BY discipline
        """, name)

    return render_template(
        "pr.html",
        my_results=my_results,
        search_results=search_results,
        is_admin=session.get("admin")
    )


# =========================================================
# START APP
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)