from flask import request, render_template, session, redirect
from helpers import login_required, error
import psycopg2
from app import app
from dotenv import load_dotenv
import os
import variables
from tasks import energy_info
from helpers import get_date
from upgrades import get_upgrades
from psycopg2.extras import RealDictCursor
load_dotenv()

@app.route("/provinces", methods=["GET"])
@login_required
def provinces():

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"))

    db = connection.cursor()

    cId = session["user_id"]

    db.execute("""SELECT cityCount, population, provinceName, id, land, happiness, productivity, energy
    FROM provinces WHERE userId=(%s) ORDER BY id ASC""", (cId,))
    provinces = db.fetchall()

    connection.close()

    return render_template("provinces.html", provinces=provinces)

@app.route("/province/<pId>", methods=["GET"])
@login_required
def province(pId):

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        cursor_factory=RealDictCursor)

    db = connection.cursor()
    cId = session["user_id"]

    upgrades = get_upgrades(cId)

    # Object under which the data about a province is stored

    try:
        db.execute("""SELECT id, userId AS user, provinceName AS name, population, pollution, happiness, productivity,
        consumer_spending, cityCount, land, energy AS electricity FROM provinces WHERE id=(%s)""", (pId,))
        province = dict(db.fetchone())
    except:
        return error(404, "Province doesn't exist")

    db.execute("SELECT location FROM stats WHERE id=%s", (cId,))
    province["location"] = dict(db.fetchone())["location"]
    province["free_cityCount"] = province["citycount"] - get_free_slots(pId, "city")
    province["free_land"] = province["land"] - get_free_slots(pId, "land")
    province["own"] = province["user"] == cId

    # Selects values for province buildings from the database and assigns them to vars
    db.execute("""SELECT * FROM proInfra WHERE id=%s""", (pId,))
    units = dict(db.fetchone())

    def enough_consumer_goods(user_id):
        db.execute("SELECT SUM(population) AS population FROM provinces WHERE userId=%s", (user_id,))
        population = dict(db.fetchone())["population"]
        db.execute("SELECT consumer_goods FROM resources WHERE id=%s", (user_id,))
        consumer_goods = (dict(db.fetchone()))["consumer_goods"]
        consumer_goods_needed = round(population * 0.000003)
        new_consumer_goods = consumer_goods - consumer_goods_needed
        return new_consumer_goods > 0

    enough_consumer_goods = enough_consumer_goods(province["user"])

    def enough_rations(user_id):
        db.execute("SELECT rations FROM resources WHERE id=%s", (user_id,))
        rations = dict(db.fetchone())["rations"]
        rations_minus = province["population"] // variables.RATIONS_PER
        return rations - rations_minus > 1

    enough_rations = enough_rations(province["user"])

    def has_power(province_id):
        db.execute("SELECT energy FROM provinces WHERE id=%s", (province_id,))
        energy = (dict(db.fetchone()))["energy"]
        return energy > 0

    energy = {}

    has_power = has_power(pId)
    energy["consumption"], energy["production"] = energy_info(pId)

    infra = variables.INFRA

    connection.close()

    return render_template("province.html", province=province, units=units,
    enough_consumer_goods=enough_consumer_goods, enough_rations=enough_rations, has_power=has_power,
    energy=energy, infra=infra, upgrades=upgrades)

def get_province_price(user_id):

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"))

    db = connection.cursor()

    db.execute("SELECT COUNT(id) FROM provinces WHERE userId=(%s)", (user_id,))
    current_province_amount = db.fetchone()[0]

    multiplier = 1 + (0.16 * current_province_amount)
    price = int(8000000 * multiplier)

    return price

@app.route("/createprovince", methods=["GET", "POST"])
@login_required
def createprovince():

    cId = session["user_id"]

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"))

    db = connection.cursor()

    if request.method == "POST":

        pName = request.form.get("name")

        db.execute("SELECT gold FROM stats WHERE id=(%s)", (cId,))
        current_user_money = int(db.fetchone()[0])

        province_price = get_province_price(cId)

        if province_price > current_user_money:
            return error(400, "You don't have enough money")

        db.execute("INSERT INTO provinces (userId, provinceName) VALUES (%s, %s) RETURNING id", (cId, pName))
        province_id = db.fetchone()[0]

        db.execute("INSERT INTO proInfra (id) VALUES (%s)", (province_id,))

        new_user_money = current_user_money - province_price
        db.execute("UPDATE stats SET gold=(%s) WHERE id=(%s)", (new_user_money, cId))

        connection.commit()
        connection.close()

        return redirect("/provinces")
    else:
        price = get_province_price(cId)
        return render_template("createprovince.html", price=price)

def get_free_slots(pId, slot_type): # pId = province id

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"))

    db = connection.cursor()

    if slot_type == "city":

        db.execute(
        """
        SELECT
        coal_burners + oil_burners + hydro_dams + nuclear_reactors + solar_fields +
        gas_stations + general_stores + farmers_markets + malls + banks +
        city_parks + hospitals + libraries + universities + monorails
        FROM proInfra WHERE id=%s
        """, (pId,))
        used_slots = int(db.fetchone()[0])

        db.execute("SELECT cityCount FROM provinces WHERE id=%s", (pId,))
        all_slots = int(db.fetchone()[0])

        free_slots = all_slots - used_slots

    elif slot_type == "land":

        db.execute(
        """
        SELECT
        army_bases + harbours + aerodomes + admin_buildings + silos +
        farms + pumpjacks + coal_mines + bauxite_mines +
        copper_mines + uranium_mines + lead_mines + iron_mines +
        lumber_mills + component_factories + steel_mills + ammunition_factories +
        aluminium_refineries + oil_refineries FROM proInfra WHERE id=%s
        """, (pId,))
        used_slots = int(db.fetchone()[0])

        db.execute("SELECT land FROM provinces WHERE id=%s", (pId,))
        all_slots = int(db.fetchone()[0])

        free_slots = all_slots - used_slots

    return free_slots

@app.route("/<way>/<units>/<province_id>", methods=["POST"])
@login_required
def province_sell_buy(way, units, province_id):

    cId = session["user_id"]

    connection = psycopg2.connect(
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"))

    db = connection.cursor()

    try:
        db.execute("SELECT id FROM provinces WHERE id=%s AND userId=%s", (province_id, cId,))
        ownProvince = db.fetchone()[0]
        ownProvince = True
    except TypeError:
        ownProvince = False

    if not ownProvince:
        return error(400, "You don't own this province")

    allUnits = [
        "land", "cityCount",

        "coal_burners", "oil_burners", "hydro_dams", "nuclear_reactors", "solar_fields",
        "gas_stations", "general_stores", "farmers_markets", "malls", "banks",
        "city_parks", "hospitals", "libraries", "universities", "monorails",

        "army_bases", "harbours", "aerodomes", "admin_buildings", "silos",

        "farms", "pumpjacks", "coal_mines", "bauxite_mines",
        "copper_mines", "uranium_mines", "lead_mines", "iron_mines",
        "lumber_mills",

        "component_factories", "steel_mills", "ammunition_factories",
        "aluminium_refineries", "oil_refineries"
    ]

    city_units = [
        "coal_burners", "oil_burners", "hydro_dams", "nuclear_reactors", "solar_fields",
        "gas_stations", "general_stores", "farmers_markets", "malls", "banks",
        "city_parks", "hospitals", "libraries", "universities", "monorails",
    ]

    land_units = [
        "army_bases", "harbours", "aerodomes", "admin_buildings", "silos",
        "farms", "pumpjacks", "coal_mines", "bauxite_mines",
        "copper_mines", "uranium_mines", "lead_mines", "iron_mines",
        "lumber_mills", "component_factories", "steel_mills",
        "ammunition_factories", "aluminium_refineries", "oil_refineries"
    ]

    db.execute("SELECT gold FROM stats WHERE id=(%s)", (cId,))
    gold = int(db.fetchone()[0])

    try:
        wantedUnits = int(request.form.get(units))
    except:
        return error(400, "You have to enter a unit amount")

    if wantedUnits < 1:
        return error(400, "Units cannot be less than 1")

    def sum_cost_exp(starting_value, rate_of_growth, current_owned, num_purchased):
        M = (starting_value * (1 - pow(rate_of_growth, (current_owned + num_purchased)))) / (1 - rate_of_growth)
        N = (starting_value * (1 - pow(rate_of_growth, (current_owned)))) / (1 - rate_of_growth)
        total_cost = M - N
        return round(total_cost)

    if units == "cityCount":
        db.execute("SELECT cityCount FROM provinces WHERE id=(%s)", (province_id,))
        current_cityCount = db.fetchone()[0]

        cityCount_price = sum_cost_exp(750000, 1.09, current_cityCount, wantedUnits)
    else:
        cityCount_price = 0

    if units == "land":
        
        db.execute("SELECT land FROM provinces WHERE id=(%s)", (province_id,))
        current_land = db.fetchone()[0]

        land_price = sum_cost_exp(520000, 1.07, current_land, wantedUnits)
    else:
        land_price = 0


    # All the unit prices in this format:
    """
    unit_price: <the of the unit>,
    unit_resource (optional): {resource_name: amount} (how many of what resources it takes to build)
    unit_resource2 (optional): same as one, just for second resource
    """
    # TODO: change the unit_resource and unit_resource2 into list based system
    unit_prices = {

        "land_price": land_price,
        "cityCount_price": cityCount_price,

        "coal_burners_price": 200000,
        "coal_burners_resource": {"aluminium": 45},

        "oil_burners_price": 350000,
        "oil_burners_resource": {"aluminium": 50},

        "hydro_dams_price": 2200000,
        "hydro_dams_resource": {"steel": 120},
        "hydro_dams_resource2": {"aluminium": 60},

        "nuclear_reactors_price": 8500000,
        "nuclear_reactors_resource": {"steel": 250},

        "solar_fields_price": 500000,
        "solar_fields_resource": {"steel": 55},

        "gas_stations_price": 550000,
        "gas_stations_resource": {"steel": 50},
        "gas_stations_resource2": {"aluminium": 35},

        "general_stores_price": 1200000,
        "general_stores_resource": {"steel": 60},
        "general_stores_resource2": {"aluminium": 70},

        "farmers_markets_price": 350000,
        "farmers_markets_resource": {"steel": 75},
        "farmers_markets_resource2": {"aluminium": 80},

        "malls_price": 15500000, # Costs 12.5m
        "malls_resource": {"steel": 360},
        "malls_resource2": {"aluminium": 240},

        "banks_price": 9000000,
        "banks_resource": {"steel": 225},
        "banks_resource2": {"aluminium": 110},

        "city_parks_price": 350000,
        "city_parks_resource": {"steel": 15},

        "hospitals_price": 2300000,
        "hospitals_resource": {"steel": 140},
        "hospitals_resource2": {"aluminium": 85},

        "libraries_price": 800000,
        "libraries_resource": {"steel": 55},
        "libraries_resource2": {"aluminium": 40},

        "universities_price": 6800000, # Costs 12.5m
        "universities_resource": {"steel": 210},
        "universities_resource2": {"aluminium": 105},

        "monorails_price": 17500000,
        "monorails_resource": {"steel": 390},
        "monorails_resource2": {"aluminium": 195},

        "army_bases_price": 650000,
        "army_bases_resource": {"lumber": 80},

        "harbours_price": 1200000,
        "harbours_resource": {"steel": 210},

        "aerodomes_price": 1400000,
        "aerodomes_resource": {"aluminium": 40},
        "aerodomes_resource2": {"steel": 165},

        "admin_buildings_price": 3600000,
        "admin_buildings_resource": {"steel": 90},
        "admin_buildings_resource2": {"aluminium": 75},

        "silos_price": 21000000,
        "silos_resource": {"steel": 540},
        "silos_resource2": {"aluminium": 240},

        "farms_price": 140000,
        "farms_resource": {"lumber": 10},

        "pumpjacks_price": 250000,
        "pumpjacks_resource": {"steel": 15},

        "coal_mines_price": 290000,
        "coal_mines_resource": {"lumber": 30},

        "bauxite_mines_price": 260000,
        "bauxite_mines_resource": {"lumber": 20},

        "copper_mines_price": 235000,
        "copper_mines_resource": {"lumber": 25},

        "uranium_mines_price": 380000,
        "uranium_mines_resource": {"steel": 35},

        "lead_mines_price": 220000,
        "lead_mines_resource": {"lumber": 25},

        "iron_mines_price": 310000,
        "iron_mines_resource": {"lumber": 20},

        "lumber_mills_price": 180000,

        "component_factories_price": 1200000,
        "component_factories_resource": {"steel": 20},
        "component_factories_resource2": {"aluminium": 20},

        "steel_mills_price": 900000,
        "steel_mills_resource": {"aluminium": 60},

        "ammunition_factories_price": 750000,
        "aluminium_refineries_price": 820000,
        "oil_refineries_price": 680000
    }

    if units not in allUnits:
        return error("No such unit exists.", 400)

    if units in ["land", "cityCount"]:
        table = "provinces"
    else:
        table = "proInfra"

    price = unit_prices[f"{units}_price"]

    try:
        db.execute("SELECT education FROM policies WHERE user_id=%s", (cId,))
        policies = db.fetchone()[0]
    except:
        policies = []

    if 2 in policies:
        price *= 0.96
    if 6 in policies and units == "universities":
        price *= 0.93
    if 1 in policies and units == "universities":
        price *= 1.14

    if units not in ["cityCount", "land"]:
        totalPrice = int(wantedUnits * price)
    else:
        totalPrice = price

    resources_used = []

    try:
        resource_data = list(unit_prices[f'{units}_resource'].items())[0]

        resources_used.append(resource_data)
    except KeyError:
        pass

    try:
        resource2_data = list(unit_prices[f'{units}_resource2'].items())[0]

        resources_used.append(resource2_data)
    except KeyError:
        pass

    curUnStat = f"SELECT {units} FROM {table} " +  "WHERE id=%s"
    db.execute(curUnStat, (province_id,))
    currentUnits = int(db.fetchone()[0])

    if units in city_units:
        slot_type = "city"
    elif units in land_units:
        slot_type = "land"
    else: # If unit is cityCount or land
        free_slots = 0
        slot_type = None

    if slot_type is not None:
        free_slots = get_free_slots(province_id, slot_type)

    def resource_stuff():

        for resource_data in resources_used:

            resource = resource_data[0]
            amount = resource_data[1]

            if way == "buy":

                current_resource_stat = f"SELECT {resource} FROM resources" + " WHERE id=%s"
                db.execute(current_resource_stat, (cId,))
                current_resource = int(db.fetchone()[0])

                new_resource = current_resource - (amount * wantedUnits)

                if new_resource < 0:
                    return 1

                resource_update_stat = f"UPDATE resources SET {resource}=" + "%s WHERE id=%s"
                db.execute(resource_update_stat, (new_resource, cId,))

            elif way == "sell":

                current_resource_stat = f"SELECT {resource} FROM resources" + " WHERE id=%s"
                db.execute(current_resource_stat, (cId,))
                current_resource = int(db.fetchone()[0])

                new_resource = current_resource + (amount * wantedUnits)

                resource_update_stat = f"UPDATE resources SET {resource}=" + "%s WHERE id=%s"
                db.execute(resource_update_stat, (new_resource, cId,))

    if way == "sell":

        if wantedUnits > currentUnits:  # Checks if user has enough units to sell
            return error("You don't have enough units", 400)

        unitUpd = f"UPDATE {table} SET {units}" + "=%s WHERE id=%s"
        db.execute(unitUpd, ((currentUnits - wantedUnits), province_id))

        new_money = gold + (wantedUnits * price)

        db.execute("UPDATE stats SET gold=(%s) WHERE id=(%s)", (new_money, cId))

        resource_stuff()

    elif way == "buy":

        if int(totalPrice) > int(gold): # Checks if user wants to buy more units than he has gold
            return error("You don't have enough money", 400)

        if free_slots < wantedUnits and units not in ["cityCount", "land"]:
            return error(400, f"You don't have enough city slots to buy {wantedUnits} units. Buy more cities to fix this problem")

        res_error = resource_stuff()
        if res_error == 1:
            return error(400, "You don't have enough resources")

        db.execute("UPDATE stats SET gold=(%s) WHERE id=(%s)", (int(gold)-int(totalPrice), cId,))

        updStat = f"UPDATE {table} SET {units}" + "=%s WHERE id=%s"
        db.execute(updStat, ((currentUnits + wantedUnits), province_id))

    if way == "buy": rev_type = "expense"
    elif way == "sell": rev_type = "revenue"

    name = f"{way.capitalize()}ing {wantedUnits} {units} in a province."
    description = ""

    db.execute("INSERT INTO revenue (user_id, type, name, description, date, resource, amount) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
    (cId, rev_type, name, description, get_date(), units, wantedUnits,))

    connection.commit()
    connection.close()

    return redirect(f"/province/{province_id}")
