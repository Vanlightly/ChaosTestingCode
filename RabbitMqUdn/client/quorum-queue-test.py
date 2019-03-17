#!/usr/bin/env python
import pika
import sys
import time
import subprocess
import random
import threading
import requests
import json

from command_args import get_args, get_mandatory_arg, get_optional_arg
from RabbitPublisher import RabbitPublisher
from MultiTopicConsumer import MultiTopicConsumer
from QueueStats import QueueStats
from ChaosExecutor import ChaosExecutor
from printer import console_out

def get_node_ip(node_name):
    bash_command = "bash ../cluster/get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

def get_live_nodes():
    bash_command = "bash ../cluster/list-live-nodes.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    nodes = list()
    for node in nodes_line.split(' '):
        if node != '' and node.isspace() == False:
            nodes.append(node)

    return nodes

def get_node_ips(live_nodes):
    ips = list()
    for node in live_nodes:
        ips.append(get_node_ip(node))

    return ips


def create_queue(mgmt_node, queue_name, replication_factor):
    try:
        mgmt_node_ip = get_node_ip(mgmt_node)
        queue_node = "rabbit@" + mgmt_node
        r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + ",\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                auth=('jack','jack'))

        console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

        return r.status_code == 201
    except Exception as e:
        console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
        return False



def main():
    args = get_args(sys.argv)

    node_count = 3
    count = -1 # no limit
    tests = int(get_mandatory_arg(args, "--tests"))
    actions = int(get_mandatory_arg(args, "--actions"))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    queue = get_mandatory_arg(args, "--queue")
    message_type = "sequence"
    node_names = ["rabbitmq1", "rabbitmq2", "rabbitmq3"]

    for x in range(tests):

        print("")
        console_out(f"TEST RUN: {str(x)} --------------------------", "TEST RUNNER")
        subprocess.call(["bash", "../automated/setup-test-run.sh", "3", "3.8"])
        console_out(f"Waiting for cluster...", "TEST RUNNER")
        time.sleep(30)
        console_out(f"Cluster status:", "TEST RUNNER")
        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        live_nodes = get_live_nodes()
        live_ips = get_node_ips(live_nodes)
        console_out(f"Live nodes: {live_nodes}", "TEST RUNNER")

        pub_node = live_nodes[random.randint(0, len(live_nodes)-1)]
        con_node = live_nodes[random.randint(0, len(live_nodes)-1)]
        console_out(f"publish to: {pub_node}", "TEST RUNNER")
        console_out(f"consume from: {con_node}", "TEST RUNNER")

        print_mod = in_flight_max
        queue_name = queue + "_" + str(x)
        
        queue_created = False
        while queue_created == False:    
            queue_created = create_queue(pub_node, queue_name, "3")
            if queue_created == False:
                time.sleep(5)

        time.sleep(10)

        publisher = RabbitPublisher(str(x), live_nodes, pub_node, in_flight_max, 120, print_mod)
        consumer = MultiTopicConsumer(str(x), live_nodes, True, print_mod, con_node)
        consumer.connect()
        consumer.set_queue(queue_name)

        stats = QueueStats('jack', 'jack', queue_name)
        chaos = ChaosExecutor(node_names)

        con_thread = threading.Thread(target=consumer.consume)
        con_thread.start()
        console_out("consumer started", "TEST RUNNER")

        pub_thread = threading.Thread(target=publisher.publish_direct,args=(queue_name, count, 1, 0, "sequence"))
        pub_thread.start()
        console_out("publisher started", "TEST RUNNER")

        for action_num in range(0, actions):
            wait_sec = random.randint(5, 60)
            console_out(f"waiting for {wait_sec} seconds before next action", "TEST RUNNER")
            time.sleep(wait_sec)

            console_out(f"execute chaos action {str(action_num)} of test {str(x)}", "TEST RUNNER")
            chaos.execute_chaos_action()
            subprocess.call(["bash", "../cluster/cluster-status.sh"])

        time.sleep(60)
        console_out("repairing cluster", "TEST RUNNER")
        chaos.repair()
        console_out("repaired cluster", "TEST RUNNER")
        
        publisher.stop(True)

        console_out("starting grace period for consumer to catch up", "TEST RUNNER")
        ctr = 0
        while ctr < grace_period_sec:
            if consumer.get_received_count() >= publisher.get_pos_ack_count() and len(publisher.get_msg_set().difference(consumer.get_msg_set())) == 0:
                break
            time.sleep(1)
            ctr += 1

        confirmed_set = publisher.get_msg_set()
        received_set = consumer.get_msg_set()

        lost_msgs = confirmed_set.difference(received_set)


        console_out("RESULTS------------------------------------", "TEST RUNNER")

        if len(lost_msgs) > 0:
            console_out(f"Lost messages count: {len(lost_msgs)}", "TEST RUNNER")
            for msg in lost_msgs:
                console_out(f"Lost message: {msg}", "TEST RUNNER")

        console_out(f"Confirmed count: {publisher.get_pos_ack_count()} Received count: {consumer.get_received_count()}", "TEST RUNNER")
        success = True
        if publisher.get_pos_ack_count() > consumer.get_received_count():
            console_out("FAILED TEST: LOST MESSAGES", "TEST RUNNER")
            success = False
  
        if consumer.received_out_of_order() == True:
            console_out("FAILED TEST: OUT OF ORDER MESSAGES", "TEST RUNNER")
            success = False
        
        if len(lost_msgs) > 0:
            console_out("FAILED TEST: LOST MESSAGES", "TEST RUNNER")
            success = False

        if success == True:
            console_out("TEST OK", "TEST RUNNER")

        console_out("RESULTS END------------------------------------", "TEST RUNNER")

        try:
            consumer.stop()
            con_thread.join()
            pub_thread.join()
        except Exception as e:
            console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

        console_out(f"TEST {str(x)} COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()