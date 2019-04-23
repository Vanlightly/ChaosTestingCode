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
from ProducerManager import ProducerManager
from BrokerManager import BrokerManager

def get_topic(new_cluster, args):
    is_new_topic = False
    if new_cluster:
        topic = get_mandatory_arg(args, "--new-topic")
        is_new_topic = True
    else:
        new_topic = get_optional_arg(args, "--new-topic", "")
        existing_topic = get_optional_arg(args, "--existing-topic", "")

        if new_topic == "" and existing_topic == "":
            console_out("You must provide a topic, either --new-topic or --existing-topic", "TEST_RUNNER")
            exit(1)
        elif new_topic == "":
            topic = existing_topic
        else:
            topic = new_topic
            is_new_topic = True

    return topic, is_new_topic

def main():
    args = get_args(sys.argv)

    cluster_size = get_optional_arg(args, "--cluster", "3")
    new_cluster = is_true(get_mandatory_arg(args, "--new-cluster"))
    use_blockade = is_true(get_optional_arg(args, "--use-blockade", "true"))
    image_version = get_optional_arg(args, "--image-version", "confluent")
    
    consumer_count = int(get_optional_arg(args, "--consumers", "1"))
    group_id = get_optional_arg(args, "--group-id", str(uuid.uuid1()))
    grace_period_sec = int(get_optional_arg(args, "--grace-period-sec", "300"))
    topic, is_new_topic = get_topic(new_cluster, args)
        
    partitions = get_optional_arg(args, "--partitions", "3")
    rep_factor = get_optional_arg(args, "--rep-factor", "3")


    analyze = is_true(get_optional_arg(args, "--analyze", "true"))
    producer_count = int(get_optional_arg(args, "--producers", 1))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 100))
    min_insync_reps = int(get_optional_arg(args, "--min-insync-replicas", "1"))
    unclean_failover = get_optional_arg(args, "--unclean-failover", "false")
    sequence_count = int(get_optional_arg(args, "--sequences", "1"))
    acks_mode = get_optional_arg(args, "--acks-mode", "all")
    print_mod = int(get_optional_arg(args, "--print-mod", "0"))

    if print_mod == 0:
        print_mod = in_flight_max * 3;
    
    test_number = 1
    console_out(f"Starting...", "TEST RUNNER")

    broker_manager = BrokerManager(image_version, use_blockade)
    broker_manager.deploy(cluster_size, new_cluster)

    initial_nodes = broker_manager.get_initial_nodes()
    console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")
    
    topic_name = topic
    
    if new_cluster or is_new_topic:
        mgmt_node = broker_manager.get_random_init_node()
        console_out(f"Creating topic {topic_name} using node {mgmt_node}", "TEST RUNNER")
        broker_manager.create_topic(mgmt_node, topic_name, rep_factor, partitions, min_insync_reps, unclean_failover)
    
    time.sleep(10)

    msg_monitor = MessageMonitor(print_mod, analyze)
    
    prod_manager = ProducerManager(broker_manager, "TEST RUNNER", topic_name)
    prod_manager.add_producers(producer_count, test_number, acks_mode, in_flight_max, print_mod, sequence_count)

    consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER", topic_name, group_id)
    consumer_manager.add_consumers(consumer_count, test_number)

    monitor_thread = threading.Thread(target=msg_monitor.process_messages)
    monitor_thread.start()
    
    consumer_manager.start_consumers()
    time.sleep(30)
    prod_manager.start_producers()
    

    while True:
        try:
            command = input("a=add consumer, r=remove consumer - then hit enter")
            if command == "a":
                consumer_manager.add_consumer_and_start_consumer(test_number)
            elif command == "r":
                consumer_manager.stop_and_remove_consumer()
            else:
                console_out("Unknown command", "TEST_RUNNER")
        except KeyboardInterrupt:
            console_out("Stopping producer. Starting grace period for consumers to catch up.", "TEST_RUNNER")
            prod_manager.stop_all_producers()
            break

    if producer_count > 0:
        try:
            ctr = 0
            while ctr < grace_period_sec:
                if msg_monitor.get_unique_count() >= prod_manager.get_total_pos_ack_count() and len(prod_manager.get_total_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                    break
                time.sleep(1)
                ctr += 1
        except KeyboardInterrupt:
            console_out("Grace period ended", "TEST RUNNER")

    confirmed_set = prod_manager.get_total_msg_set()
    lost_msgs = confirmed_set.difference(msg_monitor.get_msg_set())

    console_out("RESULTS------------------------------------", "TEST RUNNER")
    console_out(f"Confirmed count: {prod_manager.get_total_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")

    if analyze:
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
        msg_monitor.stop_consuming()
        monitor_thread.join()
        prod_manager.stop_all_producers()
    except Exception as e:
        console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

    console_out(f"TEST {str(test_number )} COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()