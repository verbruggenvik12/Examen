# Atletiek prestatie tracker

from cs50 import SQL
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# database verbinden
db = SQL("sqlite:///atletiek.db")

# mogelijke disciplines
DISCIPLINES = ["100m", "200m", "400m", "800m", "1500m", "5000m", "Verspringen", "Hoogspringen", "Kogelstoten", "Speerwerpen"]


# HOME


@app.route('/')
def index():
    # toon formulier + disciplines
    return render_template("index.html", disciplines=DISCIPLINES)



# PRESTATIE TOEVOEGEN


@app.route('/add', methods=['POST'])
def add():

    # naam ophalen
    name = request.form.get("name")
    if not name:
        return render_template("error.html", message="Naam is verplicht")

    # discipline ophalen
    discipline = request.form.get("discipline")
    if not discipline:
        return render_template("error.html", message="Discipline is verplicht")

    # check of discipline geldig is
    if discipline not in DISCIPLINES:
        return render_template("error.html", message="Ongeldige discipline")

    # resultaat ophalen
    result = request.form.get("result")
    if not result:
        return render_template("error.html", message="Resultaat is verplicht")

    # datum ophalen
    date = request.form.get("date")
    if not date:
        return render_template("error.html", message="Datum is verplicht")

    # opslaan in database
    db.execute(
        "INSERT INTO performances (name, discipline, result, date) VALUES (?, ?, ?, ?)",
        name, discipline, result, date
    )

    return redirect("/performances")



# ALLE PRESTATIES TONEN


@app.route("/performances")
def performances():
    # haal alles uit database
    rows = db.execute("SELECT * FROM performances ORDER BY date DESC")

    return render_template("performances.html", performances=rows)



# VERWIJDEREN


@app.route('/delete', methods=['POST'])
def delete():
    id = request.form.get("id")

    if id:
        db.execute("DELETE FROM performances WHERE id = ?", id)

    return redirect("/performances")



# PR (BESTE RESULTAAT)


@app.route("/pr")
def pr():

    # beste resultaat per discipline
    rows = db.execute("""
        SELECT discipline, MIN(result) as best
        FROM performances
        GROUP BY discipline
    """)

    return render_template("pr.html", prs=rows)



# APP START


if __name__ == '__main__':
    app.run(debug=True)