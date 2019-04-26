import pika
from pika import spec
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
        self.curr_node = 0

    def deploy(self, cluster_size, new_cluster, rmq_version):
        if new_cluster:
            subprocess.call(["bash", "../cluster/deploy-blockade-cluster.sh", str(cluster_size), rmq_version])
            console_out(f"Waiting for cluster to establish itself...", "TEST RUNNER")
            time.sleep(30)
            console_out(f"Cluster status:", "TEST RUNNER")
            subprocess.call(["bash", "../cluster/cluster-status.sh"])
        else:
            console_out(f"Using existing cluster...", "TEST RUNNER")
            subprocess.call(["bash", "../cluster/cluster-status.sh"])
            
        self.load_initial_nodes()
        self.print_log_files()
    
    def load_initial_nodes(self):
        self.init_live_nodes =  self.get_live_nodes()

    def print_log_files(self):
        for node in self.init_live_nodes:
            subprocess.call(["bash", "../cluster/print-log-file.sh", node])

    def zip_log_files(self, test_name, test_number):
        for node in self.init_live_nodes:
            subprocess.call(["bash", "../cluster/zip-log-file.sh", node, f"../client/logs/{test_name}/{test_number}"])

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

    def next_node(self):
        self.curr_node += 1
        if self.curr_node >= len(self.init_live_nodes):
            self.curr_node = 0

    def get_current_node(self):
        return self.init_live_nodes[self.curr_node]

    def create_sac_queue(self, mgmt_node, queue_name, replication_factor, queue_type):
        try:
            mgmt_node_ip = self.get_node_ip(mgmt_node)
            queue_node = "rabbit@" + mgmt_node

            if queue_type == "quorum":
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + str(replication_factor) + ",\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))
            else:
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))

                r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + str(replication_factor) + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
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
                        data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + str(replication_factor) + ",\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))
            else:
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                        auth=('jack','jack'))

                r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + str(replication_factor) + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
                        auth=('jack','jack'))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def connect(self, mgmt_node):
        try:
            credentials = pika.PlainCredentials('jack', 'jack')
            parameters = pika.ConnectionParameters(self.get_node_ip(mgmt_node),
                                                5672,
                                                '/',
                                                credentials)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            return True
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(e).__name__, e.args)
            console_out("Failed trying to connect. " + message, "TEST RUNNER")
            return False 

    def disconnect(self):
        try:
            if self.connection is not None and self.connection.is_open:
                self.connection.close()

            return True
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(e).__name__, e.args)
            console_out("Failed trying to disconnect. " + message, "TEST RUNNER")
            return False

    def declare_exchanges(self, queue_name, exchanges):
        if self.connect(self.get_random_init_node()):
            for exchange_name in exchanges:
                self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
                self.channel.queue_bind(queue=queue_name, exchange=exchange_name)
            console_out("Declared exchanges and queue with bindings", "TEST RUNNER")
            self.disconnect()
        else:
            console_out("Could not connect to declare exchanges and queue", "TEST RUNNER")

    def get_init_node(self, index):
        next_index =  index % len(self.init_live_nodes)
        return self.init_live_nodes[next_index]
    
    def get_random_init_node(self):
        index = random.randint(1, len(self.init_live_nodes))
        return self.get_init_node(index)