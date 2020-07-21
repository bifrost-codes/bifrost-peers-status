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
    "12D3KooWHjmfpAdrjL7EvZ7Zkk4pFmkqKDLL5JDENc7oJdeboxJJ",
    "12D3KooWBMjifHHUZxbQaQZS9t5jMmTDtZbugAtJ8TG9RuX4umEY",
    "12D3KooWLt3w5tadCR5Fc7ZvjciLy7iKJ2ZHq6qp4UVmUUHyCJuX",
    "12D3KooWMduQkmRVzpwxJuN6MQT4ex1iP9YquzL4h5K9Ru8qMXtQ",
    "12D3KooWLAHZyqMa9TQ1fR7aDRRKfWt857yFMT3k2ckK9mhYT9qR"
]

# boot nodes
peers = [
    {"peer_address": "wss://n1.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "wss://n2.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "wss://n3.testnet.liebi.com", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://n4.testnet.liebi.com:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://n5.testnet.liebi.com:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://180.153.57.47:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://36.111.41.35:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://47.101.139.226:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://47.113.188.132:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://36.111.41.50:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://36.111.35.66:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://119.3.28.151:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://159.89.147.233:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://125.94.83.242:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
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
    try:
        # async with websockets.connect(peer_id, close_timeout=5) as websocket:
        websocket = await asyncio.wait_for(websockets.connect(peer_id), 10)
        await websocket.send(param)

        resp = await websocket.recv()
        resp = json.loads(resp)
        for peer_id, val in resp['result']['connectedPeers'].items():
            if peer_id not in boot_nodes_id: # need to filter boot nodes
                status.update({f"{peer_id}": f"{val['versionString']}"})
    except:
        print("peer is down: ", peer_id, "at: ", time.time())
    
    return status

def filter_peers_status(current_status, all_status):
    current_peers_id = current_status.keys()
    all_peers_id = all_status.keys()
    
    for curr_id in current_peers_id:
        if curr_id in all_peers_id:
            all_status[curr_id]['duration'] += 1
            # update peer network id
            all_status[curr_id]['peer_version'] = current_status[curr_id]
        else:
            new_status = { f"{curr_id}": { "peer_version": f"{current_status[curr_id]}", "duration": 1 }}
            all_status.update(new_status)

    return all_status

async def update_peers_online_status():
    report = read_data()
    current_status = {}
    for peer in peers:
        status = {}
        print("get peer: ", peer['peer_address'])
        t1 = time.time()

        try:
            status = await get_networkState(peer['peer_address'], peer['param'])
        except:
            print("failed to create websocket client.")
            
        print(f"{peer['peer_address']} time cost: {time.time() - t1}")
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

if __name__ == "__main__":
    try:
        updated_times = 0
        while True:
            t1 = time.time()
            try:
                asyncio.get_event_loop().run_until_complete(update_peers_online_status())
            except:
                print("some exception happened.")
            updated_times += 1
            t2 = time.time()
            print(f"updated times: {updated_times}")
            print(f"time cost: {t2 - t1}")
            time.sleep(60 * 3)
    except KeyboardInterrupt:
        print('going to exit.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
