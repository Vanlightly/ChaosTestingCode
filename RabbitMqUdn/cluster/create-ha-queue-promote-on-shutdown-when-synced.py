import requests
import json
import sys

username = 'jack'
password = 'jack'
mgmt_node = sys.argv[1]
queue = sys.argv[2]
queue_node = sys.argv[3]

def get_node_ip(node_name):
    bash_command = "bash get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

mgmt_node_ip = get_node_ip(mgmt_node)

r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue, 
        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{},\"node\":\"" + queue_node + "\"}",
        auth=(username,password))

print(r)

r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
        data = "{\"pattern\":\"\", \"definition\": {\"ha-mode\":\"all\", \"ha-promote-on-shutdown\": \"when-synced\"}, \"priority\":0, \"apply-to\": \"queues\"}",
        auth=(username,password))

print(r)