#!/usr/bin/env python3

import json, os, os.path, sys, time
from substrateinterface import SubstrateInterface
from substrateinterface.utils import ss58

custom_types = {
    "types": {
        "Balance": "u128",
        "Cost": "u128",
        "Income": "u128",
        "TokenSymbol": {
          "type": "enum",
          "value_list": ["aUSD", "DOT", "vDOT", "KSM", "vKSM", "EOS", "vEOS"]
        },
        "AccountAsset": {
            "type": "struct",
            "type_mapping": [
                ["balance","Balance"],
                ["locked","Balance"],
                ["available", "Balance"],
                ["cost", "Cost"],
                ["income", "Income"]
            ]
        }
    }   
}

encluded_list = [
    "bixYxFRJkFMwMRnSCH9GQbYsurmL6n88eKnh6ron8ZvgwTY",
    "cgUeaC4T7BCyx4CVX3HXvee2PUqqM5bE1VFVHNccovXeJEs",
    "fw9DNydGr6yDbe4PF2yd9JX5HY7LZLFGAaRXXAJTuW3MdE7",
    "gdQsRpCjaJLrFPrRu7Grw7Dz7APivbGzDxAcJ5DhLPpnwmj"
]

# file name
validators_report = "validators_report1.json"
backup_validators_report = "/home/validators_report_backup.json"

all_validators_report = "all_validators_report.json"
backup_all_validators_report = "/home/backup_all_validators_report.json"

def read_data(validators_report, backup_validators_report):
    data = '{}'

    if os.path.isfile(backup_validators_report) and os.path.isfile(validators_report):
        # both files exist, just read sumarized_report
        f = open(backup_validators_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    elif os.path.isfile(backup_validators_report) and not os.path.isfile(validators_report):
        # just backup file exists, and copy it as sumarized_report
        shutil.copy2(backup_validators_report, validators_report)

        # read data from backup_sumarized_report,
        f = open(backup_validators_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    elif not os.path.isfile(backup_validators_report) and os.path.isfile(validators_report):
        # just backup file do not exist, just read data from sumarized_report,
        # and backup file will be copy later
        f = open(validators_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    else:
        # both files do not exist, just create sumarized_report
        open(validators_report, "w").close

    os.chmod(validators_report, 0o777)
    return json.loads(data)

def write_data(path, data):
    f = open(path, "w")
    f.write(data)
    f.truncate()
    f.close()

def update_validator_points(last_all_validators_points, current_validators_points, era_index):
    if current_validators_points == None:
        return
    if str(era_index) in last_all_validators_points.keys():
        for current_validator in current_validators_points:
            current_address = current_validator['address']
            current_points = current_validator['block_point']
            all_addresses = []
            for last_validator in last_all_validators_points[str(era_index)]:
                # this address was validator at some point
                if current_address == last_validator['address']:
                    last_validator['block_point'] = current_points
                all_addresses.append(last_validator['address'])
            # new validator
            if current_address not in all_addresses:
                last_all_validators_points[str(era_index)].append(current_validator)
    else:
        new_era_points = { str(era_index): current_validators_points}
        last_all_validators_points.update(new_era_points)

def create_bifrost_instance(address):
    bifrost = SubstrateInterface(
        url=address,
        address_type=42,
        type_registry={}
    )
    return bifrost

def get_current_era_index(bifrost):
    era_index = bifrost.get_runtime_state(
        module='Staking',
        storage_function='CurrentEra',
        params=[]
    )
    return era_index['result']

def get_current_validators_points(bifrost, era_index):
    points = bifrost.get_runtime_state(
        module='Staking',
        storage_function='ErasRewardPoints',
        params=[era_index]
    )

    if points['result'] == None:
        return None

    total = points['result']['total']
    individual = points['result']['individual']
    all_points = []
    for validator in individual:
        try:
            address = ss58.ss58_encode(validator['col1'], address_type=6)
            print(address)
        except Exception as e:
            print("failed to encode address: ", e)
            continue

        if address in encluded_list:
            continue

        # get cross chain times
        # cross_times = get_cross_chain_times(address, bifrost)
        cross_times = None
        if cross_times == None:
            cross_times = [0, 0]

        # get vtoken
        # veos, vksm, vdot = get_vtoken_assets(address, bifrost)

        points = validator['col2']
        current_reward = {
            "address": address,
            "block_point": points,
            "corss_chain": {
                "eos_bifrost": cross_times[0],
                "bifrost_eos": cross_times[1]
            },
            "vtoken_balance": {
                "vksm": 0,
                "vdot": 0,
                "veos": 0
            }
        }
        all_points.append(current_reward)
    print("all points: ", all_points)
    return all_points

def get_vtoken_assets(who, bifrost):
    veos = bifrost.get_runtime_state(
        module='Assets',
        storage_function='AccountAssets',
        params=[["vEOS", who]]
    )
    vksm = bifrost.get_runtime_state(
        module='Assets',
        storage_function='AccountAssets',
        params=[["vKSM", who]]
    )
    vdot = bifrost.get_runtime_state(
        module='Assets',
        storage_function='AccountAssets',
        params=[["vDOT", who]]
    )

    return veos['result']['balance'], vksm['result']['balance'], vdot['result']['balance']

def get_cross_chain_times(who, bifrost):
    cross_times = bifrost.get_runtime_state(
        module='BridgeEos',
        storage_function='TimesOfCrossChainTrade',
        params=[who]
    )
    return cross_times['result']

if __name__ == '__main__':
    ws_address = "wss://n2.testnet.liebi.com"
    updated_times = 0
    while True:
        try:
            t1 = time.time()

            last_all_validators_points = read_data(validators_report, backup_validators_report)
            bifrost = create_bifrost_instance(ws_address)
            era_index = get_current_era_index(bifrost)

            if era_index == None:
                t2 = time.time()
                print(f"failed to get era index")
                time.sleep(3 * 2)
                continue

            points = get_current_validators_points(bifrost, 0)

            if points == None:
                t2 = time.time()
                print(f"failed to get validator points")
                time.sleep(3 * 2)
                continue

            update_validator_points(last_all_validators_points, points, era_index)
            new_report = json.dumps(last_all_validators_points)
            write_data(validators_report, new_report)

            # get all addresses
            # all_addresses = []
            # for key in all_points.keys():
            #     for validator in all_points[key]:
            #         all_addresses.append(validator['address'])

            # # remove deplicated address
            # all_addresses = set(all_addresses)

            # # update all points
            # max_era_index = 0
            # all_points_list = []
            # latest_vtoken_details = None
            # for key in all_points.keys():
            #     if max_era_index < int(key):
            #         max_era_index = int(key)
            #         latest_vtoken_details = all_points[key]

            #     for _ in all_points[key]:
            #         pass
                


            updated_times += 1
            t2 = time.time()
            print(f"updated times: {updated_times}")
            print(f"time cost: {t2 - t1}")
            time.sleep(3 * 2)
        except KeyboardInterrupt:
            print('going to exit.')
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
