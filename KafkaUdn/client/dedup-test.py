#!/usr/bin/env python
import sys
import time
import subprocess
import random
import threading
import requests
import json
import uuid

from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true
from KafkaProducer import KafkaProducer
from KafkaConsumer import KafkaConsumer
from ChaosExecutor import ChaosExecutor
from printer import console_out
from MessageMonitor import MessageMonitor
from ConsumerManager import ConsumerManager
from BrokerManager import BrokerManager

def main():
    args = get_args(sys.argv)

    tests = int(get_mandatory_arg(args, "--tests"))
    run_minutes = int(get_mandatory_arg(args, "--run-minutes"))
    consumer_count = 1
    topic = get_mandatory_arg(args, "--topic")
    idempotence = is_true(get_mandatory_arg(args, "--idempotence"))
    partitions = 1

    cluster_size = get_optional_arg(args, "--cluster", "3")
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10000))
    buffering_max = int(get_optional_arg(args, "--buffering-max-ms", 0))
    min_insync_reps = 1
    unclean_failover = "false"
    sequence_count = 1
    rep_factor = get_optional_arg(args, "--rep-factor", "3")
    acks_mode = get_optional_arg(args, "--acks-mode", "all")
    print_mod = int(get_optional_arg(args, "--print-mod", "0"))
    new_cluster = is_true(get_optional_arg(args, "--new-cluster", "true"))
    group_id = get_optional_arg(args, "--group-id", str(uuid.uuid1()))

    if print_mod == 0:
        print_mod = in_flight_max * 3;

    for test_number in range(tests):

        print("")
        console_out(f"TEST RUN: {str(test_number)} with idempotence={idempotence}--------------------------", "TEST RUNNER")
        broker_manager = BrokerManager("confluent", True)
        
        if new_cluster:
            broker_manager.deploy(cluster_size, True)
            
        broker_manager.load_initial_nodes()
        initial_nodes = broker_manager.get_initial_nodes()
        console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")
        broker_manager.correct_advertised_listeners()

        topic_name = topic + "_" + str(test_number)
        mgmt_node = broker_manager.get_random_init_node()
        console_out(f"Creating topic {topic_name} using node {mgmt_node}", "TEST RUNNER")
        broker_manager.create_topic(mgmt_node, topic_name, rep_factor, partitions, min_insync_reps, unclean_failover)
        
        time.sleep(10)

        msg_monitor = MessageMonitor(print_mod, True)
        chaos = ChaosExecutor(broker_manager)
        
        pub_node = broker_manager.get_random_init_node()
        producer = KafkaProducer(test_number, 1, broker_manager, acks_mode, in_flight_max, print_mod)
        
        if idempotence:
            producer.create_idempotent_producer(10000000, buffering_max)
        else:
            producer.create_producer(1000000, buffering_max)

        producer.configure_as_sequence(sequence_count)
        
        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        pub_thread = threading.Thread(target=producer.start_producing,args=(topic_name, 1000000000))
        pub_thread.start()
        console_out("producer started", "TEST RUNNER")

        init_wait_sec = 20
        console_out(f"Will start chaos and consumer actions in {init_wait_sec} seconds", "TEST RUNNER")
        time.sleep(init_wait_sec)

        chaos_thread = threading.Thread(target=chaos.start_kill_leader_or_connections,args=(topic_name, 0))
        chaos_thread.start()
        console_out("Chaos executor started", "TEST RUNNER")

        ctr = 1
        while ctr < run_minutes:
            time.sleep(60)
            console_out(f"Test at {ctr} minute mark, {run_minutes-ctr} minutes left", "TEST RUNNER")
            ctr += 1

        producer.stop_producing()

        try:
            chaos.stop_chaos_actions()
            chaos_thread.join()
            console_out(f"Chaos executor shutdown", "TEST RUNNER")
        except Exception as e:
            console_out("Failed to stop chaos cleanly: " + str(e), "TEST RUNNER")
        

        subprocess.call(["bash", "../cluster/cluster-status.sh"])
        time.sleep(60)
        
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER", topic_name, group_id)
        consumer_manager.add_consumers(consumer_count, test_number)
        consumer_manager.start_consumers()
        
        ctr = 0
        
        while ctr < 300:
            if msg_monitor.get_unique_count() >= producer.get_pos_ack_count() and len(producer.get_msg_set().difference(msg_monitor.get_msg_set())) == 0:
               break
            time.sleep(1)
            ctr += 1

        confirmed_set = producer.get_msg_set()
        lost_msgs = confirmed_set.difference(msg_monitor.get_msg_set())
        duplicates = msg_monitor.get_receive_count() - msg_monitor.get_unique_count()

        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Confirmed count: {producer.get_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")
        console_out(f"Duplication count: {duplicates}", "TEST RUNNER")

        success = True
        if len(lost_msgs) > 0:
            console_out(f"FAILED TEST: Lost messages: {len(lost_msgs)}", "TEST RUNNER")
            success = False

        if idempotence and msg_monitor.get_out_of_order():
            success = False
            console_out(f"FAILED TEST: Received out-of-order messages", "TEST RUNNER")

        if idempotence and duplicates:
            success = False
            console_out(f"FAILED TEST: Duplicates", "TEST RUNNER")

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