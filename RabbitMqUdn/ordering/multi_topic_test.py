#!/usr/bin/env python
import sys
import time
import subprocess
import threading
import sync_publisher
import multi_topic_consumer

class MultiTopicTestRunner:

    node_names = []
    nodes = []
    publishers = []
    publisher_count = 0
    consumer = None

    def get_node_index(self, node_name):
        index = 0
        for node in self.node_names:
            if node == node_name:
                return index

            index +=1

        return -1

    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def find_nodes(self, connect_node):
        self.node_names = ['rabbitmq1', 'rabbitmq2', 'rabbitmq3']
            
        for node_name in self.node_names:
            self.nodes.append(self.get_node_ip(node_name))

        self.curr_node = self.get_node_index(connect_node)
    
    def create_cluster(self):
        subprocess.call(["bash", "setup-test-run.sh"])

    def consume(self, min_proc_ms, max_proc_ms):
        self.consumer.consume(min_proc_ms, max_proc_ms)

    def start_consumer(self, queue_name, exchange_prefix, exchange_count, min_proc_ms, max_proc_ms):
        exchanges = []
        for i in range(exchange_count):
            exchanges.append(f"{exchange_prefix}{i}")

        self.consumer = multi_topic_consumer.MultiTopicConsumer()
        self.consumer.connect(self.nodes[self.curr_node])
        self.consumer.declare(queue_name, exchanges)
        r = threading.Thread(target=self.consume, args=(min_proc_ms, max_proc_ms))
        r.start()
        
    def prepare_publishers(self, exchange_prefix, publisher_count):
        self.publisher_count = publisher_count
        for i in range(publisher_count):
            p = sync_publisher.SyncPublisher()
            p.connect(self.nodes[self.curr_node])
            p.declare(f"{exchange_prefix}{i}")
            self.publishers.append(p)
            self.curr_node += 1
            if self.curr_node > 2:
                self.curr_node = 0

    def publish_sequence(self, limit, wait_seconds):
        pi = 0
        for i in range(limit):
            p = self.publishers[pi]
            p.publish(i)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            pi += 1
            if pi >= self.publisher_count:
                pi = 0

    def close(self):
        for p in self.publishers:
            p.disconnect()
        
        self.consumer.disconnect()

    def run_test(self, deploy_cluster, exchange_prefix, exchange_count, message_count, wait_seconds, min_proc_ms, max_proc_ms):
        if deploy_cluster:
            self.create_cluster()

        self.find_nodes("rabbitmq1")
        self.prepare_publishers(exchange_prefix, exchange_count)
        self.start_consumer(f"queue_{exchange_prefix}", exchange_prefix, exchange_count, min_proc_ms, max_proc_ms)
        self.publish_sequence(message_count, wait_seconds)
        time.sleep(10)
        self.close()

deploy_cluster = sys.argv[1] == "true"
exchange_prefix = sys.argv[2]
exchange_count = int(sys.argv[3])
message_count = int(sys.argv[4])
wait_seconds = float(sys.argv[5])/1000
min_proc_ms = int(sys.argv[6])
max_proc_ms = int(sys.argv[7])


test_runner = MultiTopicTestRunner()
test_runner.run_test(deploy_cluster, exchange_prefix, exchange_count, message_count, wait_seconds, min_proc_ms, max_proc_ms)