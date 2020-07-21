# bifrost-peers-status

Sumarize how long the peer is online. And it will generate a status file along with this script.

### Requirements:
- python 3.6+
- pip3 install websockets
- pip3 install httpx

### Run it

1. Locate file **sumarize-peers-online-duration-by_telemetry.py**, find both lines:
```python
bifrost_chain_id = "Bifrost Asgard CC1"
network_state_api = "https://telemetry.polkadot.io/network_state/Bifrost%20Asgard%20CC1/"
```
And modify them as:
```python
bifrost_chain_id = "Bifrost Asgard CC2"
network_state_api = "https://telemetry.polkadot.io/network_state/Bifrost%20Asgard%20CC2/"
```

2. Give paths to save node status.
```python
sumarized_report = "sumarized_report.json"
backup_sumarized_report = "sumarized_report_backup.json"
```
Whatever paths you want choose.