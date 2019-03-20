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

def get_init_node(live_nodes, index):
    next_index =  index % len(live_nodes)
    return live_nodes[next_index]

def main():
    args = get_args(sys.argv)

    node_count = 3
    count = -1 # no limit
    tests = int(get_mandatory_arg(args, "--tests"))
    actions = int(get_mandatory_arg(args, "--actions"))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    cluster_size = get_optional_arg(args, "--cluster", "3")
    queue = get_mandatory_arg(args, "--queue")
    message_type = "sequence"
    
    for x in range(tests):

        print("")
        console_out(f"TEST RUN: {str(x)} --------------------------", "TEST RUNNER")
        subprocess.call(["bash", "../automated/setup-test-run.sh", cluster_size, "3.8"])
        console_out(f"Waiting for cluster...", "TEST RUNNER")
        time.sleep(30)
        console_out(f"Cluster status:", "TEST RUNNER")
        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        live_nodes = get_live_nodes()
        live_ips = get_node_ips(live_nodes)
        console_out(f"Live nodes: {live_nodes}", "TEST RUNNER")

        pub_node = live_nodes[random.randint(0, len(live_nodes)-1)]
        
        print_mod = 5000
        queue_name = queue + "_" + str(x)
        
        queue_created = False
        while queue_created == False:    
            queue_created = create_queue(pub_node, queue_name, cluster_size)
            if queue_created == False:
                time.sleep(5)

        time.sleep(10)

        publisher = RabbitPublisher(str(x), live_nodes, pub_node, in_flight_max, 120, print_mod)
        consumer1_node = get_init_node(live_nodes, 1)
        console_out(f"Consumer 0 will first connect to {consumer1_node}", "TEST RUNNER")
        consumer1 = MultiTopicConsumer(str(x) + "-con-0", live_nodes, True, print_mod, consumer1_node)
        consumer1.connect()
        consumer1.set_queue(queue_name)
#
        consumer2_node = get_init_node(live_nodes, 2)
        console_out(f"Consumer 1 will first connect to {consumer2_node}", "TEST RUNNER")
        consumer2 = MultiTopicConsumer(str(x) + "-con-1", live_nodes, True, print_mod, consumer2_node)
        consumer2.connect()
        consumer2.set_queue(queue_name)

        consumer3_node = get_init_node(live_nodes, 3)
        console_out(f"Consumer 2 will first connect to {consumer3_node}", "TEST RUNNER")
        consumer3 = MultiTopicConsumer(str(x) + "-con-2", live_nodes, True, print_mod, consumer3_node)
        consumer3.connect()
        consumer3.set_queue(queue_name)

        stats = QueueStats('jack', 'jack', queue_name)
        chaos = ChaosExecutor(live_nodes)

        con_thread1 = threading.Thread(target=consumer1.consume)
        con_thread1.start()
        console_out("consumer 1 started", "TEST RUNNER")

        con_thread2 = threading.Thread(target=consumer2.consume)
        con_thread2.start()
        console_out("consumer 2 started", "TEST RUNNER")

        con_thread3 = threading.Thread(target=consumer3.consume)
        con_thread3.start()
        console_out("consumer 3 started", "TEST RUNNER")

        pub_thread = threading.Thread(target=publisher.publish_direct,args=(queue_name, count, 1, 0, "sequence"))
        pub_thread.start()
        console_out("publisher started", "TEST RUNNER")

        consumers = [consumer1, consumer2, consumer3]
        consumer_threads = [con_thread1, con_thread2, con_thread3]

        init_wait_sec = 20
        console_out(f"Will execute first action in {init_wait_sec} seconds", "TEST RUNNER")
        time.sleep(init_wait_sec)

        for action_num in range(0, actions):
            console_out(f"execute action {str(action_num)} of test {str(x)}", "TEST RUNNER")

            running_cons = 0
            for con in consumers:
                if con.terminate == False:
                    running_cons += 1

            if running_cons > 1 and random.randint(0, 1) == 1:
                console_out(f"execute chaos and repair action", "TEST RUNNER")
                chaos.single_action_and_repair(120)
            else:
                con_index = random.randint(0, 2)
                con = consumers[con_index]
                if con.terminate == True:
                    console_out(f"Starting consumer {con_index}", "TEST RUNNER")
                    conn_ok = con.connect()
                    if conn_ok:
                        consumer_threads[con_index] = threading.Thread(target=con.consume)
                        consumer_threads[con_index].start()
                else:
                    console_out(f"Stopping consumer {con_index}", "TEST RUNNER")
                    try:
                        con.stop()
                        consumer_threads[con_index].join()
                    except Exception as e:
                        template = "An exception of type {0} occurred. Arguments:{1!r}"
                        message = template.format(type(ex).__name__, ex.args)
                        console_out(f"Failed to stop consumer correctly: {message}", "TEST RUNNER")


                time.sleep(60)
                


        time.sleep(60)
        console_out("Resuming consumers", "TEST RUNNER")
        for con_index in range(0, len(consumers)):
            if consumers[con_index].terminate == True:
                console_out(f"Starting consumer {con_index}", "TEST RUNNER")
                conn_ok = consumers[con_index].connect()
                if conn_ok:
                    consumer_threads[con_index] = threading.Thread(target=consumers[con_index].consume)
                    consumer_threads[con_index].start()
        
        publisher.stop(True)
        console_out("starting grace period for consumer to catch up", "TEST RUNNER")
        ctr = 0
        
        receive_total = 0
        received_set = set()
        while ctr < grace_period_sec:
            for con in consumers:
                receive_total += con.get_received_count()
                received_set = received_set.union(con.get_msg_set())

            if receive_total >= publisher.get_pos_ack_count() and len(publisher.get_msg_set().difference(received_set)) == 0:
                break
            time.sleep(1)
            ctr += 1

        confirmed_set = publisher.get_msg_set()
        not_consumed_msgs = confirmed_set.difference(received_set)

        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Confirmed count: {publisher.get_pos_ack_count()} Received count: {receive_total}", "TEST RUNNER")

        success = True
        if len(not_consumed_msgs) > 0:
            console_out(f"FAILED TEST: Potential failure to promote Waiting to Active. Not consumed count: {len(not_consumed_msgs)}", "TEST RUNNER")
            success = False

        for con_index in range(0, len(consumers)):
            if consumers[con_index].received_out_of_order() == True:
                success = False
                console_out(f"FAILED TEST: Consumer {con_index} received out-of-order messages", "TEST RUNNER")

        if success:
            console_out("TEST OK", "TEST RUNNER")

        console_out("RESULTS END------------------------------------", "TEST RUNNER")

        try:
            for con in consumers:
                con.stop()

            for con_thread in consumer_threads:
                con_thread.join()

            pub_thread.join()
        except Exception as e:
            console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

        console_out(f"TEST {str(x)} COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()