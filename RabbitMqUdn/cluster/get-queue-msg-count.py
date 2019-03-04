
import requests
import json
import sys
import subprocess

username = 'jack'
password = 'jack'
mgmt_node = sys.argv[1]
queue = sys.argv[2]

def get_node_ip(node_name):
    bash_command = "bash get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

mgmt_node_ip = get_node_ip(mgmt_node)
r = requests.get('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue,
        auth=(username,password))

json_text = r.json()

print(json_text["messages"])