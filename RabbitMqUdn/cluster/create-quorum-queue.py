import requests
import json
import sys
import subprocess

username = 'jack'
password = 'jack'
mgmt_node = sys.argv[1]
queue = sys.argv[2]
replication_factor = sys.argv[3]
queue_node = "rabbit@" + sys.argv[4]

def get_node_ip(node_name):
    bash_command = "bash get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

mgmt_node_ip = get_node_ip(mgmt_node)
r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue, 
        data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + "},\"node\":\"" + queue_node + "\"}",
        auth=(username,password))

print(r)