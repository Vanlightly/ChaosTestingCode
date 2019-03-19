import pika
from pika import spec
import sys
import time
import subprocess
import datetime
import uuid
import random

class ChaosExecutor(object):
    def __init__(self, node_names):
        self.chaos_actions = ["node", "node", "partition", "partition", "network"]
        self.sac_actions = ["node", "partition"]
        self.partition_state = "healed"
        self.network_state = "fast"
        self.network_actions = ["slow-network-one", "slow-network-all", "flaky-network-one", "flaky-network-all"]
        self.node_names = node_names

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

    def choose_live_victim(self):
        live_nodes = self.get_live_nodes()
        if len(live_nodes) == 1:
            return live_nodes[0]

        node_index = random.randint(0, len(live_nodes)-1)
        return live_nodes[node_index]

    def execute_chaos_action(self):
        chaos_action = self.chaos_actions[random.randint(0, len(self.chaos_actions)-1)]
        live_nodes = self.get_live_nodes()

        if len(live_nodes) == 1:
            chaos_action = "node"
        
        if chaos_action == "node":
            action_taken = False
            while action_taken == False:
                node_index = random.randint(0, len(self.node_names)-1)
                victim = self.node_names[node_index]

                if len(live_nodes) <= 1 and victim in live_nodes:
                    continue
                elif victim in live_nodes:
                    subprocess.call(["bash", "../cluster/kill-node.sh", victim])
                    action_taken = True
                else:
                    subprocess.call(["bash", "../cluster/start-node.sh", victim])
                    action_taken = True

        elif chaos_action == "partition":
            if self.partition_state == "healed":
                victim = self.choose_live_victim()
                subprocess.call(["bash", "../cluster/isolate-node.sh", victim])
                self.partition_state = "partitioned"
            else:
                if random.randint(0, 1) == 1:
                    victim = self.choose_live_victim()
                    subprocess.call(["bash", "../cluster/isolate-node.sh", victim])
                    self.partition_state = "partitioned"
                else:
                    subprocess.call(["bash", "../cluster/heal-partitions.sh"])
                    self.partition_state = "healed"

        elif chaos_action == "network":
            
            if self.network_state == "fast":
                network_action = self.network_actions[random.randint(0, 3)]
                if network_action == "slow-network-one":
                    victim = self.choose_live_victim()
                    subprocess.call(["bash", "../cluster/slow-network.sh", victim])
                elif network_action == "slow-network-all":
                    for victim in live_nodes:
                        subprocess.call(["bash", "../cluster/slow-network.sh", victim])
                elif network_action == "flaky-network-one":
                    victim = self.choose_live_victim()
                    subprocess.call(["bash", "../cluster/flaky-network.sh", victim])
                elif network_action == "flaky-network-all":
                    for victim in live_nodes:
                        subprocess.call(["bash", "../cluster/flaky-network.sh", victim])

                self.network_state = "slow/flaky"
            else:
                for victim in live_nodes:
                    subprocess.call(["bash", "../cluster/restore-network.sh", victim])
                self.network_state = "fast"
        
    def repair(self):
        live_nodes = self.get_live_nodes()
        for node in self.node_names:
            if node not in live_nodes:
                subprocess.call(["bash", "../cluster/start-node.sh", node])

        time.sleep(5)

        if self.network_state != "fast":
            subprocess.call(["bash", "../cluster/restore-network.sh", "all"])
            self.network_state = "fast"
        
        if self.partition_state != "healed":
            subprocess.call(["bash", "../cluster/heal-partitions.sh"])
            self.partition_state = "healed"

    def single_action_and_repair(self, duration_seconds):
        chaos_action = self.sac_actions[random.randint(0, len(self.sac_actions)-1)]
        live_nodes = self.get_live_nodes()

        if chaos_action == "node":
            node_index = random.randint(0, len(live_nodes)-1)
            victim = live_nodes[node_index]
            subprocess.call(["bash", "../cluster/kill-node.sh", victim])

            # 33% chance of killing two nodes
            if random.randint(0, 2) == 2:
                live_nodes = self.get_live_nodes()
                node_index = random.randint(0, len(live_nodes)-1)
                victim = live_nodes[node_index]
                subprocess.call(["bash", "../cluster/kill-node.sh", victim])

        elif chaos_action == "partition":
            victim = self.choose_live_victim()
            subprocess.call(["bash", "../cluster/isolate-node.sh", victim])
            self.partition_state = "partitioned"

        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        time.sleep(duration_seconds)
        self.repair()
        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        time.sleep(duration_seconds)
