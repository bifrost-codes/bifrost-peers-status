#!/usr/bin/env python3

import asyncio
import collections
import datetime
import json
import httpx
import os
import os.path
import random
import sys
import shutil
import time
import websockets # pip3 install websockets

# these nodes should not be counted in.
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
    {"peer_address": "ws://n4.testnet.liebi.com:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
    {"peer_address": "ws://n5.testnet.liebi.com:9944", "param": '{"id":1, "jsonrpc":"2.0", "method": "system_networkState", "params": []}'},
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

telemetry_feed = ("wss://telemetry.polkadot.io/feed/", "{}")
bifrost_chain_id = "Bifrost Asgard CC1"
network_state_api = "https://telemetry.polkadot.io/network_state/Bifrost%20Asgard%20CC1/"
odd = False

my_lock = asyncio.Lock()

async def get_all_bifrost_nodes(feed):
    nodes = {}
    try:
        websocket = await asyncio.wait_for(websockets.connect(feed[0]), 10)
        await websocket.send(feed[1])

        resp = await websocket.recv()
        nodes = json.loads(resp)
    except Exception as e:
        print("telemetry server is down: ", feed[0], "at: ", '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))

    nodes_count = 0
    if nodes != {}:
        for node in nodes:
            if isinstance(node, list):
                if node[0] == bifrost_chain_id:
                    nodes_count = node[1]
                    break
    else:
        nodes_count = 500 # 500 nodes by default
    
    return nodes_count

async def get_network_state_from_telemetry(client):
    tasks = []
    nodes_count = await get_all_bifrost_nodes(telemetry_feed)
    print("current node count: ", nodes_count)

    start = 0
    global odd
    if odd:
        odd = False
    else:
        odd = True
        start = 1

    # odd = true, (1, nodes_count), step = 2
    # odd = false, (0, nodes_count), step = 2
    for i in range(start, nodes_count, 2): 
        url = network_state_api + str(i)
        try:
            fut = get_signle_node_state(i, client, url)
            tasks.append(fut)
        except Exception as e:
            print("exception happened: ", e)

    all_telemetry_states = []
    try:
        all_telemetry_states = await asyncio.gather(*tasks, return_exceptions=False)
        print("task length: ", len(all_telemetry_states))
    except Exception as e:
        print("exception happened: ", e)

    all_state_dict = {}
    for state in all_telemetry_states:
        if state != {}:
            all_state_dict.update(state)

    return all_state_dict

async def get_signle_node_state(i, client, url):
    connectedPeers = {}
    sleep = random.uniform(1.0, 5.0)
    await asyncio.sleep(sleep)
    try:
        async with my_lock:
            resp = await client.get(url)
            print(i, resp.status_code)
            peers = resp.json()['connectedPeers']
            # filter the peer has above 30 connected peers and ensure it's not bootnode
            # if len(peers) >= 30 and resp.json()['peerId'] not in boot_nodes_id:
            if resp.json()['peerId'] not in boot_nodes_id:
                # connectedPeers = peers
                for peer_id, val in peers.items():
                    if peer_id not in boot_nodes_id: # need to filter boot nodes
                        connectedPeers.update({f"{peer_id}": f"{val['versionString']}"})
    except Exception as e:
        print("node i happened connection lost: ", i, e)
    
    return connectedPeers

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

async def get_network_state(peer_id, param):
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
        print("peer is down: ", peer_id, "at: ", '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))
    
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

async def update_peers_online_status(client):
    report = read_data()
    current_status = {}

    # 1. find all peers from bootnodes
    for peer in peers:
        status = {}
        print("get peer: ", peer['peer_address'])
        t1 = time.time()

        try:
            status = await get_network_state(peer['peer_address'], peer['param'])
        except:
            print("failed to create websocket client.")
            
        print(f"{peer['peer_address']} time cost: {time.time() - t1}")
        current_status.update(status)
        # ensure these peers doesn't have the same remote peer
        for peer_id, version in status.items():
            if peer_id not in current_status.keys():
                current_status.update({f"{peer_id}": f"{val}"})

    new_report = filter_peers_status(current_status, report)

    # 2. find some peers from telemetry in case those peers don't connect to bootnodes
    all_telemetry_states = await get_network_state_from_telemetry(client)
    # print("telemetry length: ", all_telemetry_states)
    print("telemetry length: ", len(all_telemetry_states))
    new_report = filter_peers_status(all_telemetry_states, new_report)

    # sorted by duration
    new_report = collections.OrderedDict(sorted(new_report.items(), key = lambda x: x[1]['duration'], reverse=True)) 
    new_report = json.dumps(new_report)
    write_data(sumarized_report, new_report)

    shutil.copy2(sumarized_report, backup_sumarized_report) # back it up every 5 minutes

if __name__ == "__main__":
    try:
        updated_times = 0
        client = httpx.AsyncClient()
        update_duration = 60 * 5
        while True:
            t1 = time.time()
            try:
                asyncio.get_event_loop().run_until_complete(update_peers_online_status(client))
            except Exception as e:
                print("Exception happened: ", e)
            updated_times += 1
            t2 = time.time()
            print(f"updated times: {updated_times}")
            print(f"time cost: {t2 - t1}")
            # time.sleep(60 * 3)
            time_cost = t2 - t1
            if update_duration > time_cost:
                time.sleep(update_duration - time_cost)
    except KeyboardInterrupt:
        print('going to exit.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
