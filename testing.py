import sqlite3

def generate_province_revenue(): # Runs each turn

    infra = {
    'oil_burners_plus': {'energy': 3},
    'oil_burners_money': 60000,
    'oil_burners_pollution': 25,

    'hydro_dams_plus': {'energy': 6},
    'hydro_dams_money': 250000,

    'nuclear_reactors_plus': {'energy': 12}, #  Generates 12 energy to the province
    'nuclear_reactors_money': 1200000, # Costs $1.2 million to operate nuclear reactor for each turn

    'solar_fields_plus': {'energy': 3},
    'solar_fields_money': 150000,
    }

    conn = sqlite3.connect('affo/aao.db') # connects to db
    db = conn.cursor()

    columns = ['oil_burners', 'hydro_dams', 'nuclear_reactors', 'solar_fields']

    infra_ids = db.execute("SELECT id FROM proInfra").fetchall()

    for unit in columns:
        
        plus_data = next(iter(infra[f'{unit}_plus'].items()))

        plus_resource = plus_data[0]
        plus_amount = plus_data[1]

        operating_costs = int(infra[f'{unit}_money'])

        try:
            pollution_amount = int(infra[f'{unit}_pollution'])
        except KeyError:
            pollution_amount = None
        
        """
        print(f"Unit: {unit}")
        print(f"Add {plus_amount} to {plus_resource}")
        print(f"Remove ${operating_costs} as operating costs")
        print(f"\n")
        """
        
        for province_id in infra_ids:

            province_id = province_id[0]

            user_id = db.execute("SELECT userId FROM provinces WHERE id=(?)", (province_id,)).fetchone()[0]

            unit_amount = db.execute(f"SELECT {unit} FROM proInfra WHERE id=(?)", (province_id,)).fetchone()[0]

            if unit_amount == 0:
                continue
            else:
                ### REMOVING RESOURCE

                plus_amount *= unit_amount
                operating_costs *= unit_amount
                if pollution_amount != None:
                    pollution_amount *= unit_amount
                    
                ### ADDING ENERGY
                current_plus_resource = db.execute(f"SELECT {plus_resource} FROM provinces WHERE id=(?)", (user_id,)).fetchone()[0]
                new_resource_number = current_plus_resource + plus_amount # 12 is how many uranium it generates
                db.execute(f"UPDATE provinces SET {plus_resource}=(?) WHERE id=(?)", (new_resource_number, user_id))
                ### REMOVING MONEY
                current_money = int(db.execute("SELECT gold FROM stats WHERE id=(?)", (user_id,)).fetchone()[0])
                if current_money < operating_costs:
                    continue
                else:
                    new_money = current_money - operating_costs
                    db.execute("UPDATE stats SET gold=(?) WHERE id=(?)", (new_money, user_id))
                    if pollution_amount != None:
                        current_pollution = db.execute("SELECT pollution FROM provinces WHERE id=(?)", (province_id,)).fetchone()[0]
                        new_pollution = current_pollution + pollution_amount
                        db.execute("UPDATE provinces SET pollution=(?) WHERE id=(?)", (new_pollution, province_id))

        conn.commit()

    conn.close()

generate_province_revenue()