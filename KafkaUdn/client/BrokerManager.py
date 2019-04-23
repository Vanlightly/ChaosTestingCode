import sys
import time
import subprocess
import random
from printer import console_out

class BrokerManager:
    def __init__(self, image_version, use_blockade):
        self.init_live_nodes = list()
        self.image_version = image_version
        self.use_blockade = use_blockade
            
    def deploy(self, cluster_size, new_cluster):
        if new_cluster:
            if self.use_blockade:
                subprocess.call(["bash", "../cluster/deploy-blockade-cluster.sh", cluster_size, self.image_version])
                console_out(f"Waiting for cluster to establish itself...", "TEST RUNNER")
                time.sleep(30)
                console_out(f"Cluster status:", "TEST RUNNER")
                subprocess.call(["bash", "../cluster/cluster-status.sh"])
            else:
                subprocess.call(["bash", "../cluster/deploy-compose-cluster.sh", cluster_size, self.image_version])
                console_out(f"Waiting for cluster to establish itself...", "TEST RUNNER")
                time.sleep(30)
                console_out(f"Cluster status:", "TEST RUNNER")
                subprocess.call(["bash", "../cluster/cluster-status-dc.sh"])

            self.load_initial_nodes()
            self.correct_advertised_listeners()
        else:
            console_out(f"Using existing cluster...", "TEST RUNNER")
            if self.use_blockade:
                subprocess.call(["bash", "../cluster/cluster-status.sh"])
            else:
                subprocess.call(["bash", "../cluster/cluster-status-dc.sh"])

            self.load_initial_nodes()

        
    
    def load_initial_nodes(self):
        self.init_live_nodes =  self.get_live_nodes()

    def get_initial_nodes(self):
        return self.init_live_nodes

    def get_bootstrap_servers(self):
        bs = list()
        for node in self.init_live_nodes:
            node_ip = self.get_node_ip(node)
            node_port = self.get_node_port(node)
            bs.append(f"{node_ip}:{node_port}")

        return ",".join(bs)

    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def get_node_port(self, node_name):
        if self.use_blockade:
            return "9092"
        else:
            bash_command = "bash ../cluster/get-node-port.sh " + node_name
            process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            port = output.decode('ascii').replace('\n', '')
            return port

    def get_live_nodes(self):
        if self.use_blockade:
            bash_command = "bash ../cluster/list-live-nodes.sh"
        else:
            bash_command = "bash ../cluster/list-live-nodes-dc.sh"
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        nodes_line = output.decode('ascii').replace('\n', '')
        nodes = list()
        for node in nodes_line.split(' '):
            if "kafka" in node:
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
            kf_index = broker.index("kafka")
            broker_id = int(broker[kf_index+5:kf_index+6])
            port = self.get_node_port(broker)
            try:
                if self.image_version == "confluent":
                    subprocess.call(["bash", "../cluster/cp-correct-adv-listener.sh", broker, str(broker_id), broker_ip, port])
                elif self.image_version == "wurstmeister":
                    subprocess.call(["bash", "../cluster/wm-correct-adv-listener.sh", broker, str(broker_id), broker_ip])
                else:
                    raise ValueError("Non-supported Kafka image")
            except Exception as e:
                console_out(f"Could not correct advtertised listener: {e}", "TEST RUNNER")
                return False

        return True

    def create_topic(self, broker, topic_name, replication_factor, partitions, min_insync_reps, unclean_failover):
        try:
            if self.image_version == "confluent":
                subprocess.call(["bash", "../cluster/cp-create-topic.sh", broker, topic_name, str(replication_factor), str(partitions), str(min_insync_reps), str(unclean_failover)])
            elif self.image_version == "wurstmeister":
                subprocess.call(["bash", "../cluster/wm-create-topic.sh", broker, topic_name, str(replication_factor), str(partitions), str(min_insync_reps), str(unclean_failover)])
            else:
                raise ValueError("Non-supported Kafka image")
            return True
        except Exception as e:
            console_out(f"Could not create topic: {e}", "TEST RUNNER")
            return False

    def get_init_node(self, index):
        next_index =  index % len(self.init_live_nodes)
        return self.init_live_nodes[next_index]
    
    def get_random_init_node(self):
        index = random.randint(1, len(self.init_live_nodes))
        return self.get_init_node(index)