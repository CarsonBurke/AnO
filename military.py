from flask import Flask, request, render_template, session, redirect, flash
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
import datetime
import _pickle as pickle
import random
from celery import Celery
from helpers import login_required, error
import sqlite3
# from celery.schedules import crontab # arent currently using but will be later on
from helpers import get_influence, get_coalition_influence
# Game.ping() # temporarily removed this line because it might make celery not work
from app import app


@login_required
@app.route("/military", methods=["GET", "POST"])
def military():
    connection = sqlite3.connect('affo/aao.db')
    db = connection.cursor()
    cId = session["user_id"]
    if request.method == "GET":  # maybe optimise this later with css anchors
        # ground
        tanks = db.execute(
            "SELECT tanks FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        soldiers = db.execute(
            "SELECT soldiers FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        artillery = db.execute(
            "SELECT artillery FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        # air
        flying_fortresses = db.execute(
            "SELECT flying_fortresses FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        fighter_jets = db.execute(
            "SELECT fighter_jets FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        apaches = db.execute(
            "SELECT apaches FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        # water
        destroyers = db.execute(
            "SELECT destroyers FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        cruisers = db.execute(
            "SELECT cruisers FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        submarines = db.execute(
            "SELECT submarines FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        # special
        spies = db.execute(
            "SELECT spies FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        icbms = db.execute(
            "SELECT ICBMs FROM military WHERE id=(?)", (cId,)).fetchone()[0]
        nukes = db.execute(
            "SELECT nukes FROM military WHERE id=(?)", (cId,)).fetchone()[0]

        return render_template("military.html", tanks=tanks, soldiers=soldiers, artillery=artillery,
                               flying_fortresses=flying_fortresses, apaches=apaches, fighter_jets=fighter_jets,
                               destroyers=destroyers, cruisers=cruisers, submarines=submarines,
                               spies=spies, icbms=icbms, nukes=nukes
                               )


person = {"name": "galaxy"}
# easter egg probably or it has something to do with mail xD || aw thats nice
person["message"] = "Thanks guys :D, you are all so amazing."


@login_required
@app.route("/<way>/<units>", methods=["POST"])
def military_sell_buy(way, units):  # WARNING: function used only for military

    if request.method == "POST":

        cId = session["user_id"]

        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()

        allUnits = ["soldiers", "tanks", "artillery",
                    "flying_fortresses", "fighter_jets", "apaches"
                    "destroyers", "cruisers", "submarines",
                    "spies", "icbms", "nukes"]  # list of allowed units

        if units not in allUnits:
            return error("No such unit exists.", 400)

        mil_dict = {

            ## LAND

            "soldiers_price": 200, # Cost 200
            "soldiers_resource": {"rations": 2},

            "tanks_price": 8000, # Cost 8k 
            "tanks_resource": {"steel": 5},

            "artillery_price": 16000, # Cost 16k 
            "artillery_resource": {"steel": 12},

            ## AIR

            "bombers_price": 25000, # Cost 25k 
            "bombers_resource": {"aluminium": 20},
            "bombers_resource2": {"steel": 5},
            "bombers_resource3": {"components": 6},

            "fighter_jets_price": 35000, # Cost 35k 
            "fighter_jets_resource": {"aluminium": 12},
            "fighter_jets_resource2": {"components": 3},

            "apaches_price": 32000, # Cost 32k
            "apaches_resource": {"aluminium": 8},
            "apaches_resource2": {"steel": 2},
            "apaches_resource3": {"components": 4},

            ## WATER

            "destroyers_price": 30000, # Cost 30k
            "destroyers_resource": {"steel": 30},
            "destroyers_resource2": {"components": 7},

            "cruisers_price": 55000, # Cost 55k
            "cruisers_resource": {"steel": 25},
            "cruisers_resource2": {"components": 4},

            "submarines_price": 45000, # Cost 45k
            "submarines_resource": {"steel": 20},
            "submarines_resource2": {"components": 8},

            ## SPECIAL

            "spies_price": 25000, # Cost 25k
            "spies_resource": {"rations": 50}, # Costs 50 rations

            "ICBMs_price": 4000000, # Cost 4 million
            "ICMBs_resource": {"steel": 350}, # Costs 350 steel

            "nukes_price": 12000000, # Cost 12 million
            "nukes_resource": {"uranium": 800}, # Costs 800 uranium
            "nukes_resource2": {"steel": 600} # Costs 600 steel

        }

        price = 500 # rn price is 500 everywhere lol
        gold = db.execute(
            "SELECT gold FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
        wantedUnits = request.form.get(units)
        curUnStat = f'SELECT {units} FROM military WHERE id=?'
        totalPrice = int(wantedUnits) * price
        currentUnits = db.execute(curUnStat, (cId,)).fetchone()[0]

        if way == "sell":

            if int(wantedUnits) > int(currentUnits):  # checks if unit is legits
                return redirect("/too_much_to_sell")  # seems to work

            unitUpd = f"UPDATE military SET {units}=(?) WHERE id=(?)"
            db.execute(unitUpd, (int(currentUnits) - int(wantedUnits), cId))
            db.execute("UPDATE stats SET gold=(?) WHERE id=(?)", ((
                int(gold) + int(wantedUnits) * int(price)), cId,))  # clean
            flash(f"You sold {wantedUnits} {units}")

        elif way == "buy":

            if int(totalPrice) > int(gold):  # checks if user wants to buy more units than he has gold
                return redirect("/too_many_units")

            db.execute("UPDATE stats SET gold=(?) WHERE id=(?)",
                       (int(gold)-int(totalPrice), cId,))

            updStat = f"UPDATE military SET {units}=(?) WHERE id=(?)"
            # fix weird table
            db.execute(updStat, ((int(currentUnits) + int(wantedUnits)), cId))
            flash(f"You bought {wantedUnits} {units}")

        else:
            return error(404, "Page not found")

        connection.commit()
        connection.close()

        return redirect("/military")


@login_required
@app.route("/<way>/<units>/<province_id>", methods=["POST"])
# WARNING: function used only for military
def province_sell_buy(way, units, province_id):

    if request.method == "POST":

        cId = session["user_id"]

        connection = sqlite3.connect('affo/aao.db')
        db = connection.cursor()

        try:
            ownProvince = db.execute(
                "SELECT id FROM provinces WHERE id=(?) AND userId=(?)", (province_id, cId,)).fetchone()[0]
            ownProvince = True
        except TypeError:
            ownProvince = False

        if ownProvince == False:
            return error(400, "You don't own this province")

        allUnits = [
            "land", "cityCount",
            "oil_burners", "hydro_dams", "nuclear_reactors", "solar_fields",
            "gas_stations", "general_stores", "farmers_markets", "malls", "banks",
            "city_parks", "hospitals", "libraries", "universities", "monorails"
        ]

        if units not in allUnits:
            return error("No such unit exists.", 400)

        if units == "land":
            price = 100
            table = "provinces"
        elif units == "cityCount":
            price = 500
            table = "provinces"
        else:
            table = "proInfra"

        if units == "oil_burners":
            price = 350
        elif units == "hydro_dams":
            price = 450
        elif units == "nuclear_reactors":
            price = 700
        elif units == "solar_fields":
            price = 550

        elif units == "gas_stations":
            price = 500
        elif units == "general_stores":
            price = 500
        elif units == "farmers_markets":
            price = 500
        elif units == "malls":
            price = 500
        elif units == "banks":
            price = 500

        elif units == "city_parks":
            price = 500
        elif units == "hospitals":
            price = 500
        elif units == "libraries":
            price = 500
        elif units == "universities":
            price = 500
        elif units == "monorails":
            price = 500

        gold = db.execute(
            "SELECT gold FROM stats WHERE id=(?)", (cId,)).fetchone()[0]
        wantedUnits = request.form.get(units)

        curUnStat = f'SELECT {units} FROM {table} WHERE id=?'
        totalPrice = int(wantedUnits) * price
        currentUnits = db.execute(curUnStat, (province_id,)).fetchone()[0]

        if way == "sell":

            if int(wantedUnits) > int(currentUnits):  # checks if unit is legits
                # seems to work
                return error("You don't have enough units", 400)

            unitUpd = f"UPDATE {table} SET {units}=(?) WHERE id=(?)"
            db.execute(unitUpd, (int(currentUnits) -
                                 int(wantedUnits), province_id))
            db.execute("UPDATE stats SET gold=(?) WHERE id=(?)", ((
                int(gold) + int(wantedUnits) * int(price)), cId,))  # clean

        elif way == "buy":

            if int(totalPrice) > int(gold):  # checks if user wants to buy more units than he has gold
                return error("You don't have enough gold", 400)

            db.execute("UPDATE stats SET gold=(?) WHERE id=(?)",
                       (int(gold)-int(totalPrice), cId,))

            updStat = f"UPDATE {table} SET {units}=(?) WHERE id=(?)"
            # fix weird table
            db.execute(
                updStat, ((int(currentUnits) + int(wantedUnits)), province_id))

        else:
            error(404, "Page not found")

        connection.commit()
        connection.close()

        return redirect(f"/province/{province_id}")
