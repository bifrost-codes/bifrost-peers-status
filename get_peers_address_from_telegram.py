#!/usr/bin/env python3

import asyncio
import collections
import datetime
import json
import os
import os.path
import sys
import time
import re
import codecs
from telethon import TelegramClient, events, utils
from telethon.tl.types import InputMessagesFilterPhotos

#  telegram data
# apply api id and hash @https://my.telegram.org/apps
api_id = 0
api_hash = ''

# personal info
phone = ''
username = ''
code = ''

# rexp
exp = r'5[0-9a-zA-Z]{46,48}'

def write_data(path, data):
    f = open(path, "w")
    f.write(data)
    f.truncate()
    f.close()

def read_data(path):
    f = open(path, "r")
    data = f.read()
    f.close()
    return data

def find_complete_ss58_address(strs):
    t = re.finditer(exp, strs)
    s = []
    for i in t:
        s.append(i.group())
    print(len(set(s)))
    return list(set(s))

def read_html(path):
    data = {}
    f = codecs.open(path, 'r', 'utf-8')
    data = f.read()
    f.close()
    return data

def read_json(path):
    f = open(path, "r")
    data = f.read()
    f.close()

    data = json.loads(data)
    names = []
    for key, val in data.items():
        name = data[key]["peer_version"]
        t = re.finditer(r'5[a-zA-Z0-9]{8,9}', name)
        for i in t:
            names.append(i.group())
    
    print('all name: ', len(set(names)))
    return list(set(names))

async def get_chat_histotry():
    # client = TelegramClient(username, api_id, api_hash, proxy=(socks.HTTP, '127.0.0.1', 1087, True, 'log', 'pass'))
    client = await TelegramClient(username, api_id, api_hash).start()
    await client.connect()

    # Ensure you're authorized
    if not await client.is_user_authorized():
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            print('failed to connect telegram server due to: ', e)

    # watch new event
    @client.on(events.NewMessage(pattern=r'5[0-9a-zA-Z]{46,48}'))
    async def handler(event):
        sender = await event.get_sender()
        name = utils.get_display_name(sender)
        print(name, 'said', event.text, '!')
        data = read_data("activate_address.json")
        data = json.loads(data)
        
        t = re.finditer(exp, event.text)
        for i in t:
            data.append(i.group())

        write_data("activate_address.json", json.dumps(data))

    try:
        print('(Press Ctrl+C to stop this)')
        await client.run_until_disconnected()
    finally:
        await client.disconnect()

def get_addresses_from_chat_history():
    paths = ["messages.html", "messages2.html", "messages3.html", "messages4.html"]
    all_addresses = []
    for path in paths:
        data = read_html(path)
        addresses = find_complete_ss58_address(data)
        all_addresses.extend(addresses)
    print(all_addresses)
    all_addresses =list(set(all_addresses))
    all_addresses = json.dumps(all_addresses)
    write_data("activate_address.json", all_addresses)

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(get_chat_histotry())
        # get_addresses_from_chat_history()
        # json_path = "sumarized_report.json"
        # read_json(json_path)
    except KeyboardInterrupt:
        print('going to exit.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
