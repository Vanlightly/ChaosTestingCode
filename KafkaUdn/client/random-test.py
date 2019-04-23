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
    consumer_count = int(get_mandatory_arg(args, "--consumers"))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    topic = get_mandatory_arg(args, "--topic")
    partitions = get_mandatory_arg(args, "--partitions")

    cluster_size = get_optional_arg(args, "--cluster", "3")
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 100))
    min_insync_reps = int(get_optional_arg(args, "--min-insync-replicas", "1"))
    unclean_failover = get_optional_arg(args, "--unclean-failover", "false")
    sequence_count = int(get_optional_arg(args, "--sequences", "1"))
    rep_factor = get_optional_arg(args, "--rep-factor", "3")
    acks_mode = get_optional_arg(args, "--acks-mode", "all")
    print_mod = int(get_optional_arg(args, "--print-mod", "0"))
    group_id = get_optional_arg(args, "--group-id", str(uuid.uuid1()))
    include_chaos = is_true(get_optional_arg(args, "--chaos-actions", "true"))
    chaos_min_interval = int(get_optional_arg(args, "--chaos-min-interval", "60"))
    chaos_max_interval = int(get_optional_arg(args, "--chaos-max-interval", "120"))
    include_con_actions = is_true(get_optional_arg(args, "--consumer-actions", "true"))
    con_action_min_interval = int(get_optional_arg(args, "--consumer-min-interval", "20"))
    con_action_max_interval = int(get_optional_arg(args, "--consumer-max-interval", "60"))

    if print_mod == 0:
        print_mod = in_flight_max * 3;
    
    for test_number in range(tests):

        print("")
        console_out(f"TEST RUN: {str(test_number)} --------------------------", "TEST RUNNER")
        
        broker_manager = BrokerManager("confluent", True)
        broker_manager.deploy(cluster_size, True)
        
        initial_nodes = broker_manager.get_initial_nodes()
        console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")
        
        topic_name = topic + "_" + str(test_number)
        mgmt_node = broker_manager.get_random_init_node()
        console_out(f"Creating topic {topic_name} using node {mgmt_node}", "TEST RUNNER")
        broker_manager.create_topic(mgmt_node, topic_name, rep_factor, partitions, min_insync_reps, unclean_failover)
        
        time.sleep(10)

        msg_monitor = MessageMonitor(print_mod, True)
        chaos = ChaosExecutor(broker_manager)
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER", topic_name, group_id)

        producer = KafkaProducer(test_number, 1, broker_manager, acks_mode, in_flight_max, print_mod)
        producer.create_producer(0, 0)
        producer.configure_as_sequence(sequence_count)
        consumer_manager.add_consumers(consumer_count, test_number)

        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        consumer_manager.start_consumers()

        pub_thread = threading.Thread(target=producer.start_producing,args=(topic_name, 10000000))
        pub_thread.start()
        console_out("producer started", "TEST RUNNER")

        init_wait_sec = 20
        console_out(f"Will start chaos and consumer actions in {init_wait_sec} seconds", "TEST RUNNER")
        time.sleep(init_wait_sec)

        if include_chaos:
            chaos_thread = threading.Thread(target=chaos.start_random_single_action_and_repair,args=(chaos_min_interval, chaos_max_interval))
            chaos_thread.start()
            console_out("Chaos executor started", "TEST RUNNER")

        if include_con_actions:
            consumer_action_thread = threading.Thread(target=consumer_manager.start_random_consumer_actions,args=(con_action_min_interval, con_action_max_interval))
            consumer_action_thread.start()
            console_out("Consumer actions started", "TEST RUNNER")

        ctr = 0
        while ctr < run_minutes:
            try:
                time.sleep(60)
                console_out(f"Test at {ctr} minute mark, {run_minutes-ctr} minutes left", "TEST RUNNER")
                ctr += 1
            except KeyboardInterrupt:
                console_out("Stopping test early", "TEST_RUNNER")
                break

        try:
            chaos.stop_chaos_actions()
            consumer_manager.stop_random_consumer_actions()
            
            if include_chaos:
                chaos_thread.join()
            
            if include_con_actions:
                consumer_action_thread.join()
        except Exception as e:
            console_out("Failed to stop chaos cleanly: " + str(e), "TEST RUNNER")

        console_out("Resuming consumers", "TEST RUNNER")
        consumer_manager.resume_all_consumers()
        
        producer.stop_producing()
        console_out("starting grace period for consumer to catch up", "TEST RUNNER")
        ctr = 0
        
        while ctr < grace_period_sec:
            if msg_monitor.get_unique_count() >= producer.get_pos_ack_count() and len(producer.get_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                break
            time.sleep(1)
            ctr += 1

        confirmed_set = producer.get_msg_set()
        lost_msgs = confirmed_set.difference(msg_monitor.get_msg_set())

        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Confirmed count: {producer.get_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")

        success = True
        if len(lost_msgs) > 0:
            console_out(f"FAILED TEST: Lost messages: {len(lost_msgs)}", "TEST RUNNER")
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