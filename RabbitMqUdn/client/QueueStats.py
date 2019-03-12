import requests
import json
import sys
import subprocess

class QueueStats(object):
    def __init__(self, username, password, queue):
        self.username = username
        self.password = password
        self.queue = queue

    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def get_queue_length(self, node):
        mgmt_node_ip = self.get_node_ip(node)
        r = requests.get(f'http://{mgmt_node_ip}:15672/api/queues/%2F/{self.queue}',
                auth=(self.username,self.password))
        json_text = r.json()
        return json_text["messages"]