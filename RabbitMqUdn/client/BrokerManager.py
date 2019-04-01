import sys
import time
import subprocess
import random
import threading
import requests
import json
from printer import console_out

class BrokerManager:
    def __init__(self):
        self.init_live_nodes = list()
            
    def load_initial_nodes(self):
        self.init_live_nodes =  self.get_live_nodes()

    def get_initial_nodes(self):
        return self.init_live_nodes

    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def get_live_nodes(self):
        bash_command = "bash ../cluster/list-live-nodes.sh"
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        nodes_line = output.decode('ascii').replace('\n', '')
        nodes = list()
        for node in nodes_line.split(' '):
            if node != '' and node.isspace() == False:
                nodes.append(node)

        return nodes

    def get_node_ips(self, live_nodes):
        ips = list()
        for node in live_nodes:
            ips.append(self.get_node_ip(node))

        return ips


    def create_sac_queue(self, mgmt_node, queue_name, replication_factor, queue_type):
        try:
            mgmt_node_ip = self.get_node_ip(mgmt_node)
            queue_node = "rabbit@" + mgmt_node

            if queue_type == "quorum":
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + ",\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))
            else:
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))

                r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + replication_factor + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
                        auth=('jack','jack'))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def create_queue(self, mgmt_node, queue_name, replication_factor, queue_type):
        try:
            mgmt_node_ip = self.get_node_ip(mgmt_node)
            queue_node = "rabbit@" + mgmt_node

            if queue_type == "quorum":
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + ",\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))
            else:
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))

                r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + replication_factor + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
                        auth=('jack','jack'))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def get_init_node(self, index):
        next_index =  index % len(self.init_live_nodes)
        return self.init_live_nodes[next_index]
    
    def get_random_init_node(self):
        index = random.randint(1, len(self.init_live_nodes))
        return self.get_init_node(index)