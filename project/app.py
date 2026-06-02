import re
from datetime import datetime
from cs50 import SQL
from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "geheim"

# Flask-app initialiseren en secret key instellen voor sessiebeheer

@app.template_filter('format_date')
def format_date(value):
    """Format a date string to dd/mm/yyyy for display."""
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue

    return text

# Verbind met de SQLite-database
db = SQL("sqlite:///atletiek.db")

# Standaard disciplines die in formulieren beschikbaar zijn
DISCIPLINES = ["100m", "200m", "400m", "800m"]
WIND_DISCIPLINES = ["100m", "200m"]

# Zorg dat de database kolommen heeft voor windmetingen
def ensure_wind_columns():
    conn = sqlite3.connect("atletiek.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(performances)")
    columns = [row[1] for row in cursor.fetchall()]
    if "wind_speed" not in columns:
        cursor.execute("ALTER TABLE performances ADD COLUMN wind_speed REAL")
    if "wind_direction" not in columns:
        cursor.execute("ALTER TABLE performances ADD COLUMN wind_direction TEXT")
    conn.commit()
    conn.close()

ensure_wind_columns()


def parse_result_seconds(result):
    if result is None:
        return float('inf')

    try:
        return float(result)
    except Exception:
        pass

    text = str(result)
    parts = re.findall(r"\d+", text)
    if not parts:
        return float('inf')

    if len(parts) == 3:
        minutes, seconds, hundredths = parts
        return int(minutes) * 60 + int(seconds) + int(hundredths) / 100.0
    if len(parts) == 2:
        seconds, hundredths = parts
        return int(seconds) + int(hundredths) / 100.0
    if len(parts) == 1:
        return float(parts[0])

    try:
        return float(parts[0])
    except Exception:
        return float('inf')

# ---------------- HELPER FUNCTIONS ----------------

def annotate_wind(rows):
    for row in rows:
        row["invalid_wind"] = False
        row["wind_display"] = ""

        wind_speed = row.get("wind_speed")
        wind_direction = row.get("wind_direction")

        if wind_speed is None or wind_speed == "":
            continue

        try:
            # Zet de wind_speed om naar een getal voor de berekening
            wind_speed = float(str(wind_speed).replace(',', '.'))

            # Zorg dat we richting-veilig controleren door alles in kleine letters te zetten
            direction_clean = str(wind_direction).strip().lower()

            if direction_clean == "meewind":
                sign = "+"
            else:
                sign = "-"

            row["wind_display"] = f"{sign}{wind_speed:.1f} m/s"

            # DE PASSERDE LOGICA: Alleen ongeldig (rood) als het meewind is EN groter of gelijk aan 2.0
            # Tegenwind zal hierdoor NOOIT op True springen.
            if direction_clean == "meewind" and wind_speed >= 2.0:
                row["invalid_wind"] = True

        except:
            row["wind_display"] = ""

    return rows


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "Trainer" and password == "trainer123":
            session["admin"] = True
            return redirect("/admin")

        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            username, password
        )

        if len(user) == 1:
            session["user_id"] = user[0]["id"]
            return redirect("/")
        else:
            return render_template("error.html", message="Foute login")

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            request.form.get("username"),
            request.form.get("password")
        )
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- HOME ----------------
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("index.html", disciplines=DISCIPLINES)


# ---------------- ADD ----------------
@app.route("/add", methods=["POST"])
def add():
    discipline = request.form.get("discipline")
    wind_speed = request.form.get("wind_speed")
    wind_direction = request.form.get("wind_direction")

    if discipline not in WIND_DISCIPLINES:
        wind_speed = None
        wind_direction = None
    else:
        if wind_speed == "":
            wind_speed = None
        # Zorg dat we het altijd in kleine letters opslaan in de database
        if wind_direction:
            wind_direction = wind_direction.lower()
        if wind_direction not in ["meewind", "tegenwind"]:
            wind_direction = None

    db.execute("""
        INSERT INTO performances (user_id, name, discipline, result, date, wind_speed, wind_direction)
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


# ---------------- MIJN PRESTATIES ----------------
@app.route("/performances")
def performances():
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

    rows = annotate_wind(rows)
    return render_template(
        "performances.html",
        performances=rows,
        disciplines=DISCIPLINES,
        selected_discipline=discipline,
        selected_sort=sort
    )


# ---------------- ADMIN ----------------
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


# ---------------- DELETE ----------------
@app.route("/delete", methods=["POST"])
def delete():
    db.execute("DELETE FROM performances WHERE id = ?", request.form.get("id"))
    return redirect("/performances")


# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":
        discipline = request.form.get("discipline")
        wind_speed = request.form.get("wind_speed")
        wind_direction = request.form.get("wind_direction")

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

    p = db.execute("SELECT * FROM performances WHERE id = ?", id)[0]
    return render_template("edit.html", p=p, disciplines=["100m","200m","400m","800m"])


# ---------------- PR ZOEKEN ----------------
@app.route("/pr", methods=["GET", "POST"])
def pr():
    if not session.get("admin") and "user_id" not in session:
        return redirect("/login")

    if session.get("admin"):
        my_results = []
    else:
        my_results = db.execute("""
            SELECT discipline, MIN(result) as best
            FROM performances
            WHERE user_id = ?
            GROUP BY discipline
        """, session["user_id"])

    search_results = None

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


if __name__ == "__main__":
    app.run(debug=True)