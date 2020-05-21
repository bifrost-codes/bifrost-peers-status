#!/usr/bin/env python3

import asyncio
import collections
import json
import os
import os.path
import sys
import shutil
import time
import websockets # pip3 install websockets


boot_nodes_id = [
    "QmPQUbcEfMskoQBfsinAU354f3P91ENa3pcaDJsLwXbM2o",
    "QmSUwR4ppe9sB4VQCuy3itB7A2BF8BcfweLsVz83bh1vPy",
    "QmYTccenokf4hmTvpzpgrNK2UxYngNHjXguuGTkZTW8aF3",
    "Qmbpc8jNDoZVBxW4ZZGAgVUzgyUcFPrKxHvTAafjjwRVFp",
    "QmTKx4x4TCj6ptoe22Nfqr8FiCtMCicwbY34KcGt4xMvKC"
]

# boot nodes
peers = [
    {"peer_address": "wss://n1.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "wss://n2.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "wss://n3.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
]

"""
update it per hour, if there's new peers online, insert it, if existting peers're still online, duration + 1
{
    String: { peer_version: String, duration: u32 }, # { peer_id: { peer_version: String, duration: u32 }, ... }
    ...
}
"""
# file name
sumarized_report = "sumarized_report.json"
backup_sumarized_report = "/home/sumarized_report_backup.json"

def read_data():
    data = '{}'

    if os.path.isfile(backup_sumarized_report) and os.path.isfile(sumarized_report):
        # both files exist, just read sumarized_report
        f = open(backup_sumarized_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    elif os.path.isfile(backup_sumarized_report) and not os.path.isfile(sumarized_report):
        # just backup file exists, and copy it as sumarized_report
        shutil.copy2(backup_sumarized_report, sumarized_report)

        # read data from backup_sumarized_report,
        f = open(backup_sumarized_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    elif not os.path.isfile(backup_sumarized_report) and os.path.isfile(sumarized_report):
        # just backup file do not exist, just read data from sumarized_report,
        # and backup file will be copy later
        f = open(sumarized_report, "r")
        data = f.read()
        if data == "":
            data = '{}'
        f.close()
    else:
        # both files do not exist, just create sumarized_report
        open(sumarized_report, "w").close

    os.chmod(sumarized_report, 0o777)
    return json.loads(data)

def write_data(path, data):
    f = open(path, "w")
    f.write(data)
    f.truncate()
    f.close()

async def get_networkState(peer_id, param):
    status = {}
    async with websockets.connect(peer_id) as websocket:
        await websocket.send(param)

        resp = await websocket.recv()
        resp = json.loads(resp)
        for peer_id, val in resp['result']['connectedPeers'].items():
            if peer_id not in boot_nodes_id: # need to filter boot nodes
                status.update({f"{peer_id}": f"{val['versionString']}"})
    
    return status

def filter_peers_status(current_status, all_status):
    current_peers_id = current_status.keys()
    all_peers_id = all_status.keys()
    
    for curr_id in current_peers_id:
        if curr_id in all_peers_id:
            all_status[curr_id]['duration'] += 1
        else:
            new_status = { f"{curr_id}": { "peer_version": f"{current_status[curr_id]}", "duration": 1 }}
            all_status.update(new_status)

    return all_status

async def update_peers_online_status():
    updated_times = 0

    while True:
        report = read_data()
        current_status = {}
        for peer in peers:
            status = await get_networkState(peer['peer_address'], peer['param'])
            current_status.update(status)
            # ensure these peers doesn't have the same remote peer
            for peer_id, version in status.items():
                if peer_id not in current_status.keys():
                    current_status.update({f"{peer_id}": f"{val}"})

        # save it to file
        new_report = filter_peers_status(current_status, report)
        # sorted by duration
        new_report = collections.OrderedDict(sorted(new_report.items(), key = lambda x: x[1]['duration'], reverse=True)) 
        new_report = json.dumps(new_report)
        write_data(sumarized_report, new_report)

        shutil.copy2(sumarized_report, backup_sumarized_report) # back it up every 5 minutes
        updated_times += 1
        print(f"updated times: {updated_times}")

        time.sleep(60 * 3) # update it per 3 minutes

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(update_peers_online_status())
    except KeyboardInterrupt:
        print('going to exit.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
