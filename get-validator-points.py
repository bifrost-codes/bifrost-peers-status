#!/usr/bin/env python3

import json, os, os.path, sys, time
from substrateinterface import SubstrateInterface
from substrateinterface.utils import ss58


# file name
validators_report = "validators_report.json"
backup_validators_report = "/home/validators_report_backup.json"

def read_data():
    data = '[]'

    if os.path.isfile(backup_validators_report) and os.path.isfile(validators_report):
        # both files exist, just read sumarized_report
        f = open(backup_validators_report, "r")
        data = f.read()
        if data == "":
            data = '[]'
        f.close()
    elif os.path.isfile(backup_validators_report) and not os.path.isfile(validators_report):
        # just backup file exists, and copy it as sumarized_report
        shutil.copy2(backup_validators_report, validators_report)

        # read data from backup_sumarized_report,
        f = open(backup_validators_report, "r")
        data = f.read()
        if data == "":
            data = '[]'
        f.close()
    elif not os.path.isfile(backup_validators_report) and os.path.isfile(validators_report):
        # just backup file do not exist, just read data from sumarized_report,
        # and backup file will be copy later
        f = open(validators_report, "r")
        data = f.read()
        if data == "":
            data = '[]'
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

def update_validator_points(last_all_validators_points, current_validators_points):
    for current_validator in current_validators_points:
        current_address = current_validator['address']
        current_points = current_validator['points']
        new_validator = False
        for last_validator in last_all_validators_points:
            # this address was validator at some point
            if current_address == last_validator['address']:
                last_validator['points'] = current_points
                new_validator = True
        # new validator
        if not new_validator:
            last_all_validators_points.append(current_validator)

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
    all_points = []

    points = bifrost.get_runtime_state(
        module='Staking',
        storage_function='ErasRewardPoints',
        params=[era_index]
    )

    total = points['result']['total']
    individual = points['result']['individual']
    for validator in individual:
        if validator['col1'] == '0x0000000000000000000000000000000000000000000000000000000000000000':
            continue

        address = ss58.ss58_encode(validator['col1'], address_type=6)
        points = validator['col2']
        current_reward = {
            "address": address,
            "points": points
        }
        all_points.append(current_reward)
    
    return all_points

if __name__ == '__main__':
    ws_address = "wss://n2.testnet.liebi.com"
    updated_times = 0
    while True:
        try:
            t1 = time.time()

            last_all_validators_points = read_data()
            bifrost = create_bifrost_instance(ws_address)
            era_index = get_current_era_index(bifrost)
            points = get_current_validators_points(bifrost, era_index)
            print(points)
            update_validator_points(last_all_validators_points, points)
            new_report = json.dumps(last_all_validators_points)
            write_data(validators_report, new_report)

            updated_times += 1
            t2 = time.time()
            print(f"updated times: {updated_times}")
            print(f"time cost: {t2 - t1}")
            time.sleep(3 * 1)
        except KeyboardInterrupt:
            print('going to exit.')
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
