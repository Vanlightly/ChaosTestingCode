import sys
import time
import subprocess
import random
from printer import console_out

class BrokerManager:
    def __init__(self):
        self.init_live_nodes = list()
            
    def load_initial_nodes(self):
        self.init_live_nodes =  self.get_live_nodes()

    def get_initial_nodes(self):
        return self.init_live_nodes

    def get_bootstrap_servers(self):
        bs = list()
        for node in self.init_live_nodes:
            node_ip = self.get_node_ip(node)
            bs.append(f"{node_ip}:9092")

        return ",".join(bs)

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
            if node.startswith("kafka"):
                nodes.append(node)

        return nodes

    def get_node_ips(self, live_nodes):
        ips = list()
        for node in live_nodes:
            ips.append(self.get_node_ip(node))

        return ips

    def correct_advertised_listeners(self):
        for broker in self.init_live_nodes:
            broker_ip = self.get_node_ip(broker)
            broker_id = int(broker[-1:])
            try:
                cmd = f"bash ../cluster/correct-adv-listener.sh {broker} {broker_id} {broker_ip}"
                subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            except Exception as e:
                console_out("Could not correct advtertised listener", "TEST RUNNER")
                return False

        return True

    def create_topic(self, broker, topic_name, replication_factor, partitions, min_insync_reps, unclean_failover):
        try:
            cmd = f"bash ../cluster/create-topic.sh {broker} {topic_name} {replication_factor} {partitions} {min_insync_reps} {unclean_failover}"
            subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            return True
        except Exception as e:
            console_out("Could not create topic", "TEST RUNNER")
            return False

    def get_init_node(self, index):
        next_index =  index % len(self.init_live_nodes)
        return self.init_live_nodes[next_index]
    
    def get_random_init_node(self):
        index = random.randint(1, len(self.init_live_nodes))
        return self.get_init_node(index)