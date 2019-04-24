#!/usr/bin/env python
import pika
import sys
import time
import subprocess
import random
import threading
import requests
import json

from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true
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

    count = -1 # no limit
    tests = int(get_mandatory_arg(args, "--tests"))
    actions = int(get_mandatory_arg(args, "--actions"))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    cluster_size = get_optional_arg(args, "--cluster", "3")
    queue = get_mandatory_arg(args, "--queue")
    sac_enabled = is_true(get_mandatory_arg(args, "--sac"))
    chaos_mode = get_optional_arg(args, "--chaos-mode", "mixed")
    chaos_min_interval = int(get_optional_arg(args, "--chaos-min-interval", "30"))
    chaos_max_interval = int(get_optional_arg(args, "--chaos-max-interval", "120"))
    queue_type = get_mandatory_arg(args, "--queue-type")

    for test_number in range(tests):

        print("")
        console_out(f"TEST RUN: {str(test_number)} --------------------------", "TEST RUNNER")
        broker_manager = BrokerManager()
        broker_manager.deploy(cluster_size, True, "3.8")
        initial_nodes = broker_manager.get_initial_nodes()
        
        console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")

        pub_node = broker_manager.get_random_init_node()
        con_node = broker_manager.get_random_init_node()
        console_out(f"publish to: {pub_node}", "TEST RUNNER")
        console_out(f"consume from: {con_node}", "TEST RUNNER")

        print_mod = in_flight_max * 5
        queue_name = queue + "_" + str(test_number)
        
        mgmt_node = broker_manager.get_random_init_node()
        queue_created = False
        while queue_created == False:    
            if sac_enabled:
                queue_created = broker_manager.create_sac_queue(mgmt_node, queue_name, cluster_size, queue_type)
            else:
                queue_created = broker_manager.create_queue(mgmt_node, queue_name, cluster_size, queue_type)
            if queue_created == False:
                time.sleep(5)

        time.sleep(10)

        msg_monitor = MessageMonitor(print_mod, True)
        publisher = RabbitPublisher(1, test_number, broker_manager, pub_node, in_flight_max, 120, print_mod)
        publisher.configure_sequence_direct(queue_name, count, 0, 1)
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER")
        consumer_manager.add_consumers(1, test_number, queue_name)

        chaos = ChaosExecutor(initial_nodes)

        if chaos_mode == "partitions":
            chaos.only_partitions()
        elif chaos_mode == "nodes":
            chaos.only_kill_nodes()
        
        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()

        consumer_manager.start_consumers()
        
        pub_thread = threading.Thread(target=publisher.start_publishing)
        pub_thread.start()
        console_out("publisher started", "TEST RUNNER")

        for action_num in range(0, actions):
            wait_sec = random.randint(chaos_min_interval, chaos_max_interval)
            console_out(f"waiting for {wait_sec} seconds before next action", "TEST RUNNER")
            time.sleep(wait_sec)

            console_out(f"execute chaos action {str(action_num)} of test {str(test_number)}", "TEST RUNNER")
            chaos.execute_chaos_action()
            subprocess.call(["bash", "../cluster/cluster-status.sh"])

        time.sleep(60)
        console_out("repairing cluster", "TEST RUNNER")
        chaos.repair()
        console_out("repaired cluster", "TEST RUNNER")
        
        publisher.stop_publishing()

        console_out("starting grace period for consumer to catch up", "TEST RUNNER")
        ctr = 0
        
        while ctr < grace_period_sec:
            if msg_monitor.get_unique_count() >= publisher.get_pos_ack_count() and len(publisher.get_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                break
            time.sleep(1)
            ctr += 1

        confirmed_set = publisher.get_msg_set()
        lost_msgs = confirmed_set.difference(msg_monitor.get_msg_set())

        console_out("RESULTS------------------------------------", "TEST RUNNER")

        if len(lost_msgs) > 0:
            console_out(f"Lost messages count: {len(lost_msgs)}", "TEST RUNNER")
            for msg in lost_msgs:
                console_out(f"Lost message: {msg}", "TEST RUNNER")

        console_out(f"Confirmed count: {publisher.get_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")
        success = True
         
        if msg_monitor.get_out_of_order() == True:
            console_out("FAILED TEST: OUT OF ORDER MESSAGES", "TEST RUNNER")
            success = False
        
        if len(lost_msgs) > 0:
            console_out("FAILED TEST: LOST MESSAGES", "TEST RUNNER")
            success = False

        if success == True:
            console_out("TEST OK", "TEST RUNNER")

        console_out("RESULTS END------------------------------------", "TEST RUNNER")

        try:
            consumer_manager.stop_all_consumers()
            pub_thread.join()
            monitor_thread.join()
        except Exception as e:
            console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

        console_out(f"TEST {str(test_number)} COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()