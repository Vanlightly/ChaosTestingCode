import sys
import time
import subprocess
import datetime
import uuid
import random
from printer import console_out

class ChaosExecutor(object):
    def __init__(self, broker_manager):
        self.chaos_actions = ["node", "node", "partition", "partition", "network"]
        self.sac_actions = ["node", "partition"]
        self.partition_state = "healed"
        self.network_state = "fast"
        self.network_actions = ["slow-network-one", "slow-network-all", "flaky-network-one", "flaky-network-all"]
        self.broker_manager = broker_manager
        self.node_names = broker_manager.get_initial_nodes()
        self.stop_actions = False

    def choose_live_victim(self):
        live_nodes = self.broker_manager.get_live_nodes()
        if len(live_nodes) == 1:
            return live_nodes[0]

        node_index = random.randint(0, len(live_nodes)-1)
        return live_nodes[node_index]

    def execute_chaos_action(self):
        chaos_action = self.chaos_actions[random.randint(0, len(self.chaos_actions)-1)]
        live_nodes = self.broker_manager.get_live_nodes()

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
        live_nodes = self.broker_manager.get_live_nodes()
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

    def stop_chaos_actions(self):
        self.stop_actions = True
    
    def start_random_single_action_and_repair(self, chaos_min_interval, chaos_max_interval):
        while self.stop_actions == False:
            self.single_action_and_repair(chaos_min_interval, chaos_max_interval)

    def single_action_and_repair(self, chaos_min_interval, chaos_max_interval):
        duration_seconds = random.randint(chaos_min_interval, chaos_max_interval)
        chaos_action = self.sac_actions[random.randint(0, len(self.sac_actions)-1)]
        live_nodes = self.broker_manager.get_live_nodes()

        if chaos_action == "node":
            node_index = random.randint(0, len(live_nodes)-1)
            victim = live_nodes[node_index]
            subprocess.call(["bash", "../cluster/kill-node.sh", victim])

            # 33% chance of killing two nodes
            if random.randint(0, 2) == 2:
                live_nodes = self.broker_manager.get_live_nodes()
                node_index = random.randint(0, len(live_nodes)-1)
                victim = live_nodes[node_index]
                subprocess.call(["bash", "../cluster/kill-node.sh", victim])

        elif chaos_action == "partition":
            victim = self.choose_live_victim()
            subprocess.call(["bash", "../cluster/isolate-node.sh", victim])
            self.partition_state = "partitioned"

        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        self.wait_for(duration_seconds)
        self.repair()
        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        self.wait_for(duration_seconds)

    def start_kill_leader_or_connections(self, topic, partition):
        node = self.choose_live_victim()
        while not self.stop_actions:
            action_val = random.randint(0, 2)
            if action_val in [0, 1]:
                self.kill_tcp_connections()
                self.wait_for(20)
            else:
                victim = self.get_partition_leader(node, topic, partition)
                subprocess.call(["bash", "../cluster/kill-node.sh", victim])
                self.wait_for(60)
                subprocess.call(["bash", "../cluster/start-node.sh", victim])
                self.wait_for(10)
            

    def wait_for(self, seconds):
        ctr = 0
        while self.stop_actions == False and ctr < seconds:
            ctr += 1
            time.sleep(1)

    def get_blockade_interface(self):
        bash_command = f"bash ../cluster/get-blockade-interface.sh"
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        interfac = output.decode('ascii').replace('\n', '')
        return interfac

    def kill_tcp_connections(self):
        console_out("Killing connections for 10 second period", "CHAOS")
        cmd = f"sudo timeout 10s sudo tcpkill -i {self.get_blockade_interface()} -9 port 9092  > /dev/null 2>&1"
        subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

    def get_partition_leader(self, node, topic, partition):
        bash_command = f"bash ../cluster/get-partition-leader-node.sh {node} {topic} {partition}"
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        leader = output.decode('ascii').replace('\n', '')
        return leader
