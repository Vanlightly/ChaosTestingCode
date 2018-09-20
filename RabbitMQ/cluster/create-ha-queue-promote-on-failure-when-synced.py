import requests
import json
import sys

username = 'jack'
password = 'jack'
mgmt_node = sys.argv[1]
queue = sys.argv[2]
queue_node = "rabbit@" + sys.argv[3]

node_names = ['rabbitmq1', 'rabbitmq2', 'rabbitmq3']
nodes = ['172.17.0.2', '172.17.0.3', '172.17.0.4']

def get_node_index(node_name):
    index = 0
    for node in node_names:
        if node == node_name:
            return index

        index +=1

    return -1
mgmt_node_ip = nodes[get_node_index(mgmt_node)]
r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue, 
        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{},\"node\":\"" + queue_node + "\"}",
        auth=(username,password))

print(r)

r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
        data = "{\"pattern\":\"\", \"definition\": {\"ha-mode\":\"all\", \"ha-promote-on-failure\": \"when-synced\" }, \"priority\":0, \"apply-to\": \"queues\"}",
        auth=(username,password))

print(r)