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
from MessageMonitor import MessageMonitor
from ConsumerManager import ConsumerManager
from BrokerManager import BrokerManager

def main():
    args = get_args(sys.argv)

    node_count = 3
    count = -1 # no limit
    tests = int(get_mandatory_arg(args, "--tests"))
    run_minutes = int(get_mandatory_arg(args, "--run-minutes"))
    consumer_count = int(get_mandatory_arg(args, "--consumers"))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    cluster_size = get_optional_arg(args, "--cluster", "3")
    queue = get_mandatory_arg(args, "--queue")
    queue_type = get_mandatory_arg(args, "--queue-type")
    
    message_type = "sequence"
    
    for test_number in range(tests):

        print("")
        console_out(f"TEST RUN: {str(test_number)} --------------------------", "TEST RUNNER")
        subprocess.call(["bash", "../automated/setup-test-run.sh", cluster_size, "3.8"])
        console_out(f"Waiting for cluster...", "TEST RUNNER")
        time.sleep(30)
        console_out(f"Cluster status:", "TEST RUNNER")
        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        
        broker_manager = BrokerManager()
        broker_manager.load_initial_nodes()
        initial_nodes = broker_manager.get_initial_nodes()
        console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")

        print_mod = 5000
        queue_name = queue + "_" + str(test_number)
        mgmt_node = broker_manager.get_random_init_node()
        queue_created = False

        while queue_created == False:    
            queue_created = broker_manager.create_sac_queue(mgmt_node, queue_name, cluster_size, queue_type)
            if queue_created == False:
                time.sleep(5)

        time.sleep(10)

        msg_monitor = MessageMonitor(print_mod)
        stats = QueueStats('jack', 'jack', queue_name)
        chaos = ChaosExecutor(initial_nodes)
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER")

        pub_node = broker_manager.get_random_init_node()
        publisher = RabbitPublisher(str(test_number), initial_nodes, pub_node, in_flight_max, 120, print_mod)
        consumer_manager.add_consumers(consumer_count, test_number, queue_name)

        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        consumer_manager.start_consumers()

        pub_thread = threading.Thread(target=publisher.publish_direct,args=(queue_name, count, 1, 0, "sequence"))
        pub_thread.start()
        console_out("publisher started", "TEST RUNNER")

        init_wait_sec = 20
        console_out(f"Will start chaos and consumer actions in {init_wait_sec} seconds", "TEST RUNNER")
        time.sleep(init_wait_sec)

        chaos_thread = threading.Thread(target=chaos.start_random_single_action_and_repair,args=(90,))
        chaos_thread.start()
        console_out("Chaos executor started", "TEST RUNNER")

        consumer_action_thread = threading.Thread(target=consumer_manager.start_random_consumer_actions,args=(5, 30))
        consumer_action_thread.start()
        console_out("Consumer actions started", "TEST RUNNER")

        ctr = 0
        while ctr < run_minutes:
            time.sleep(60)
            ctr += 1
            console_out(f"Test at {ctr} minute mark, {run_minutes-ctr} minutes left", "TEST RUNNER")

        try:
            chaos.stop_random_single_action_and_repair()
            consumer_manager.stop_random_consumer_actions()
            chaos_thread.join()
            consumer_action_thread.join()
        except Exception as e:
            console_out("Failed to stop chaos cleanly: " + str(e), "TEST RUNNER")

        console_out("Resuming consumers", "TEST RUNNER")
        consumer_manager.resume_all_consumers()
        
        publisher.stop(True)
        console_out("starting grace period for consumer to catch up", "TEST RUNNER")
        ctr = 0
        
        while ctr < grace_period_sec:
            if msg_monitor.get_unique_count() >= publisher.get_pos_ack_count() and len(publisher.get_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                break
            time.sleep(1)
            ctr += 1

        confirmed_set = publisher.get_msg_set()
        not_consumed_msgs = confirmed_set.difference(msg_monitor.get_msg_set())

        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Confirmed count: {publisher.get_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")

        success = True
        if len(not_consumed_msgs) > 0:
            console_out(f"FAILED TEST: Potential failure to promote Waiting to Active. Not consumed count: {len(not_consumed_msgs)}", "TEST RUNNER")
            success = False

        if msg_monitor.get_out_of_order() == True:
            success = False
            console_out(f"FAILED TEST: Received out-of-order messages", "TEST RUNNER")

        if success:
            console_out("TEST OK", "TEST RUNNER")

        console_out("RESULTS END------------------------------------", "TEST RUNNER")

        try:
            consumer_manager.stop_all_consumers()
            pub_thread.join()
            msg_monitor.stop_consuming()
            monitor_thread.join()
        except Exception as e:
            console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

        console_out(f"TEST {str(test_number )} COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()