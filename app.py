from flask import Flask, request, render_template, session, redirect
from flask_session import Session
from tempfile import mkdtemp
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import login_required
from flask_mail import Mail, Message
# from celery import Celery
# from celery.schedules import crontab

app = Flask(__name__)

app.config["MAIL_SERVER"] = None # replace this with the domain of the email
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True

# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['result_backend'] = 'redis://localhost:6379/0'

# celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
# celery.conf.update(app.config)

"""@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every minute
    sender.add_periodic_task(
        crontab(minute='*/1'),
        populationGrowth.s(),
    )"""

mail = Mail(app)

# code for sending custom email messages to users
def sendEmail(title, content, user):

    conn = sqlite3.connect('affo/aao.db')

    msg = Message(title)
    msg.add_recipient("somebodyelse@example.com")
    msg.html = content
    mail.send(msg)


# basic cache configuration
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def index():
    return render_template("index.html") # renders index.html when "/" is accesed

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        connection = sqlite3.connect('affo/aao.db') # connects to db
        db = connection.cursor() # creates the cursor for db connection

        password = request.form.get("password") # gets the password input from the form
        username = request.form.get("username") # gets the username input from the forms

        if not username or not password: # checks if inputs are blank
            return redirect("/error_no_pw_or_un") #TODO change to actual error
        user = db.execute("SELECT * FROM users WHERE username = (?)", (username,)).fetchone() # selects data about user, from users
        connection.commit()

        if user is not None and check_password_hash(user[3], password): # checks if user exists and if the password is correct
            session["user_id"] = user[0] # sets session's user_id to current user's id
            session["logged_in"] = True
            print('User has succesfully logged in.')
            connection.commit()
            connection.close()
            return redirect("/") # redirects user to homepage
        return redirect("/error_wrong_pw")

    else:
        return render_template("login.html") # renders login.html when "/login" is acessed via get

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        
        # connects the db to the signup function
        connection = sqlite3.connect('affo/aao.db') # connects to db
        db = connection.cursor()

        username = request.form.get("username") # gets corresponding form inputs
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        connection.commit()
        if not confirmation or not password or not email or not username: # checks for blank inputs
            return redirect("/error_blank") #TODO change to actual error
        elif password != confirmation: # checks if password is = to confirmation password
            return redirect("/error_wrong_cn") #TODO change to actual error
        else:
            hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16) # hashes the inputted password
            db.execute("INSERT INTO users (username, email, hash) VALUES (?, ?, ?)", (username, email, hashed,)) # creates a new user
            user = db.execute("SELECT id FROM users WHERE username = (?)", (username,)).fetchone()
            connection.commit()
            session["user_id"] = user[0] # set's the user's "id" column to the sessions variable "user_id"
            session["logged_in"] = True
            db.execute("INSERT INTO stats (id) SELECT id FROM users WHERE id = (?)", (session["user_id"],)) # change the default location                                                                          # "Bosfront" to something else
            db.execute("INSERT INTO ground (id) SELECT id FROM users WHERE id = (?)", (session["user_id"],)) 
            db.execute("INSERT INTO air (id) SELECT id FROM users WHERE id = (?)", (session["user_id"],))
            db.execute("INSERT INTO water (id) SELECT id FROM users WHERE id = (?)", (session["user_id"],))
            connection.commit()
            connection.close()
            return redirect("/")
    else:
        return render_template("signup.html")

# @celery.task()
# TODO: create a celery task so this task would do itself every midnight or so
def populationGrowth():
    conn = sqlite3.connect('affo/aao.db') # connects to db
    db = conn.cursor()
    pop = db.execute("SELECT population, id FROM stats").fetchall() # selects id, population from the stats table and gets all the results for it

    for row in pop: # iterates over every result in population
        user_id = row[1] # sets the user_id variable to the "id" result from the query
        curPop = row[0]  # sets the current population variable to the "population" result from the query
        newPop = curPop + (int(curPop/10)) # gets the current population value and adds the same value / 10 to it
        db.execute("UPDATE stats SET population=(?) WHERE id=(?)", (newPop, user_id,)) # updates the db with the new value for population
        conn.commit()

    pop = db.execute("SELECT population FROM stats").fetchall()[0] # selects the population
    return pop # returns population TODO: change it so it wouldn't return population, just update the stats

@login_required
@app.route("/country/id=<cId>")
def country(cId):
    connection = sqlite3.connect('affo/aao.db')
    db = connection.cursor()
    username = db.execute("SELECT username FROM users WHERE id=(?)", (cId,)).fetchone()[0] # gets country's name from db
    connection.commit()
    population = db.execute("SELECT population FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
    happiness = db.execute("SELECT happiness FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
    connection.commit()
    location = db.execute("SELECT location FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
    gold = db.execute("SELECT gold FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
    try: # sees if user is logged in
        uId = True 
        return render_template("country.html", username=username, cId=cId, happiness=happiness, population=population,
        location=location, gold=gold, uId=uId)
    except KeyError: # if user isnt logged in
        uId = False
        return render_template("country.html", uId=uId)

@login_required
@app.route("/military", methods=["GET", "POST"])
def military():
    connection = sqlite3.connect('affo/aao.db')
    db = connection.cursor()
    cId = session["user_id"]
    if request.method == "GET":
        tanks = db.execute("SELECT tanks FROM ground WHERE id=(?)", (cId,)).fetchone()[0]
        soldiers = db.execute("SELECT soldiers FROM ground WHERE id=(?)", (cId,)).fetchone()[0]
        artillery = db.execute("SELECT artillery FROM ground WHERE id=(?)", (cId,)).fetchone()[0]
        destroyers = db.execute("SELECT destroyers FROM water WHERE id=(?)", (cId,)).fetchone()[0]
        flying_fortresses = db.execute("SELECT flying_fortresses FROM air WHERE id=(?)", (cId,)).fetchone()[0]
        connection.commit()
        return render_template("military.html", tanks=tanks, soldiers=soldiers,
        artillery=artillery, destroyers=destroyers, flying_fortresses=flying_fortresses)

@login_required
@app.route("/market", methods=["GET", "POST"])
def market():
    if request.method == "GET":
        return render_template("market.html")

@login_required
@app.route("/coalition", methods=["GET", "POST"])
def coalition():
    if request.method == "GET":
        return render_template("coalition.html")

@login_required
@app.route("/establish_coalition", methods=["GET", "POST"])
def establish_coalition():
    if request.method == "POST":
        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()

        name = request.form.get("name")

        db.execute("INSERT INTO colNames (name) VALUES (?)", (name,))
        colId = db.execute("SELECT id FROM colNames WHERE name = (?)", (name,)).fetchone()[0]
        db.execute("INSERT INTO coalitions (colId, userId) VALUES (?, ?)", (colId, session["user_id"],))

        connection.commit()
        return redirect("/coalition")
    else:
        return render_template("establish_coalition.html")


@login_required
@app.route("/createprovince", methods=["GET", "POST"])
def createprovince():
    if request.method == "GET":
        return render_template("createprovince.html")

@login_required
@app.route("/marketoffer", methods=["GET", "POST"])
def marketoffer():
    if request.method == "GET":
        return render_template("marketoffer.html")

@login_required
@app.route("/countries")
def countries():
    if request.method == "GET":
        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()
        name = db.execute("SELECT username FROM users").fetchall()
        population = db.execute("SELECT population FROM stats").fetchall()
        countryId = db.execute("SELECT id FROM users").fetchall()
        connection.commit()
        zipped = zip(name, population, countryId)
        return render_template("countries.html", zipped=zipped)

@login_required
@app.route("/coalitions", methods=["GET", "POST"])
def coalitions():
    if request.method == "GET":
        return render_template("coalitions.html")

@login_required
@app.route("/buy/<units>", methods=["POST"])
def buy(units):
    if request.method == "POST":

        cId = session["user_id"]

        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()

        allUnits = ["soldiers", "tanks", "artillery", "flying_fortresses", "destroyers"] # all allowed units
        if units not in allUnits:
            return redirect("/no_such_unit")

        if units == "soldiers": # maybe change this to a dict later on
            table = "ground"
            price = 50
        elif units == "tanks":
            table = "ground"
            price = 150
        elif units == "artillery":
            table = "ground"
            price = 300
        elif units == "flying_fortresses":
            table = "air"
            price = 500
        elif units == "destroyers":
            table = "water"
            price = 500

        gold = db.execute("SELECT gold FROM stats WHERE id=(?)", (cId,)).fetchone()[0]

        wantedUnits = request.form.get(units)
        totalPrice = int(wantedUnits) * price
        curUnStat = f"SELECT {units} FROM {table} WHERE id=(?)"
        currentUnits = db.execute(curUnStat,(cId,)).fetchone()[0]

        if int(totalPrice) > int(gold): # checks if user wants to buy more units than he has gold
            return redirect("/too_many_units")

        db.execute("UPDATE stats SET gold=(?) WHERE id=(?)", (int(gold)-int(totalPrice), cId,))

        updStat = f"UPDATE {table} SET {units}=(?) WHERE id=(?)"
        db.execute(updStat,((int(currentUnits) + int(wantedUnits)), cId)) # fix weird table

        connection.commit()

        return redirect("/military")

@login_required
@app.route("/sell/<units>", methods=["POST"])
def sell(units):
    if request.method == "POST":
    
        cId = session["user_id"]

        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()

        allUnits = ["soldiers", "tanks", "artillery", "flying_fortresses", "destroyers"]
        if units not in allUnits:
            return redirect("/no_such_unit")

        if units == "soldiers": # maybe change this to a dict later on
            table = "ground"
            price = 50
        elif units == "tanks":
            table = "ground"
            price = 150
        elif units == "artillery":
            table = "ground"
            price = 300
        elif units == "flying_fortresses":
            table = "air"
            price = 500
        elif units == "destroyers":
            table = "water"
            price = 500

        gold = db.execute("SELECT gold FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
        wantedUnits = request.form.get(units)
        curUnitsStatement = f'SELECT {units} FROM {table} WHERE id=?'
        currentUnits = db.execute(curUnitsStatement,(cId,)).fetchone()[0] #  seems to work

        if int(wantedUnits) > int(currentUnits): # checks if unit is legits
            return redirect("/too_much_to_sell") # seems to work

        unitUpd = f"UPDATE {table} SET {units}=(?) WHERE id=(?)"
        db.execute(unitUpd,(int(currentUnits) - int(wantedUnits), cId)) # not working
        db.execute("UPDATE stats SET gold=(?) WHERE id=(?)", ((int(gold) + int(wantedUnits) * int(price)), cId,)) # clean

        connection.commit()

        return redirect("/military")

# available to run if double click the file
if __name__ == "__main__":
    app.run(debug=True)

