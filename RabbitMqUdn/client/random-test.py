#!/usr/bin/env python
import pika
import sys
import time
import subprocess
import random
import threading
import requests
import json
import signal
import datetime

from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true
from RabbitPublisher import RabbitPublisher
from MultiTopicConsumer import MultiTopicConsumer
from QueueStats import QueueStats
from ChaosExecutor import ChaosExecutor
from printer import console_out, console_out_exception
from MessageMonitor import MessageMonitor
from ConsumerManager import ConsumerManager
from BrokerManager import BrokerManager

stop_please = False
stop_requests = 0

def interuppt_handler(signum, frame):
    global stop_please, stop_requests
    console_out("STOP REQUESTED", "TEST RUNNER")
    stop_please = True
    stop_requests +=1

    if stop_requests >= 2:
        sys.exit(-2) 
    

def main():
    print("random-test.py")
    #signal.signal(signal.SIGINT, interuppt_handler)
    args = get_args(sys.argv)

    count = -1 # no limit
    test_name = get_mandatory_arg(args, "--test-name")
    tests = int(get_mandatory_arg(args, "--tests"))
    run_minutes = int(get_mandatory_arg(args, "--run-minutes"))
    consumer_count = int(get_mandatory_arg(args, "--consumers"))
    prefetch = int(get_optional_arg(args, "--pre-fetch", "10"))
    grace_period_sec = int(get_mandatory_arg(args, "--grace-period-sec"))
    queue = get_mandatory_arg(args, "--queue")
    queue_type = get_mandatory_arg(args, "--queue-type")
    sac_enabled = is_true(get_mandatory_arg(args, "--sac"))
    consumer_hard_close = is_true(get_optional_arg(args, "--consumer-hard-close", str(sac_enabled)))
    log_messages = is_true(get_optional_arg(args, "--log-msgs", "false"))

    publisher_count = int(get_optional_arg(args, "--publishers", "1"))
    if publisher_count > 0:
        in_flight_max = int(get_optional_arg(args, "--in-flight-max", "10"))
        print_mod = int(get_optional_arg(args, "--print-mod", f"{in_flight_max * 5}"))
        sequence_count = int(get_optional_arg(args, "--sequences", "1"))
    else:
        print_mod = int(get_optional_arg(args, "--print-mod", f"1000"))

    new_cluster = is_true(get_optional_arg(args, "--new-cluster", "true"))
    cluster_size = get_optional_arg(args, "--cluster", "3")
    rmq_version = get_optional_arg(args, "--rmq-version", "3.8")

    include_chaos = is_true(get_optional_arg(args, "--chaos-actions", "true"))
    if include_chaos:
        chaos_mode = get_optional_arg(args, "--chaos-mode", "mixed")
        chaos_min_interval = int(get_optional_arg(args, "--chaos-min-interval", "60"))
        chaos_max_interval = int(get_optional_arg(args, "--chaos-max-interval", "120"))
    
    include_con_actions = is_true(get_optional_arg(args, "--consumer-actions", "true"))
    if include_con_actions:
        con_action_min_interval = int(get_optional_arg(args, "--consumer-min-interval", "20"))
        con_action_max_interval = int(get_optional_arg(args, "--consumer-max-interval", "60"))

    failed_test_log = list()
    failed_tests = set()

    for test_number in range(tests):

        print("")
        subprocess.call(["mkdir", f"logs/{test_name}/{str(test_number)}"])
        console_out(f"TEST RUN: {str(test_number)} --------------------------", "TEST RUNNER")
        broker_manager = BrokerManager()
        broker_manager.deploy(cluster_size, new_cluster, rmq_version)
        initial_nodes = broker_manager.get_initial_nodes()
        console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")

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

        msg_monitor = MessageMonitor(test_name, test_number, print_mod, True, log_messages)
        chaos = ChaosExecutor(initial_nodes)

        if include_chaos:
            if chaos_mode == "partitions":
                chaos.only_partitions()
            elif chaos_mode == "nodes":
                chaos.only_kill_nodes()

        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        if consumer_count > 0:
            consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER")
            consumer_manager.add_consumers(consumer_count, test_number, queue_name, prefetch)
            consumer_manager.start_consumers()

        if publisher_count == 1:
            publisher = RabbitPublisher(1, test_number, broker_manager, in_flight_max, 120, print_mod)
            publisher.configure_sequence_direct(queue_name, count, 0, sequence_count)

            pub_thread = threading.Thread(target=publisher.start_publishing)
            pub_thread.start()
            console_out("publisher started", "TEST RUNNER")

        if include_con_actions or include_chaos:
            init_wait_sec = 20
            console_out(f"Will start chaos and consumer actions in {init_wait_sec} seconds", "TEST RUNNER")
            time.sleep(init_wait_sec)

        if include_chaos:
            chaos_thread = threading.Thread(target=chaos.start_random_single_action_and_repair,args=(chaos_min_interval,chaos_max_interval))
            chaos_thread.start()
            console_out("Chaos executor started", "TEST RUNNER")

        if include_con_actions:
            consumer_action_thread = threading.Thread(target=consumer_manager.start_random_consumer_actions,args=(con_action_min_interval, con_action_max_interval, consumer_hard_close))
            consumer_action_thread.start()
            console_out("Consumer actions started", "TEST RUNNER")

        
        ctr = 0
        run_seconds = run_minutes * 60
        while ctr < run_seconds and not stop_please:
            try:
                time.sleep(1)
                ctr += 1

                if ctr % 60 == 0:
                    console_out(f"Test at {int(ctr/60)} minute mark, {int((run_seconds-ctr)/60)} minutes left", "TEST RUNNER")
            except KeyboardInterrupt:
                console_out(f"Test forced to stop at {int(ctr/60)} minute mark, {int((run_seconds-ctr)/60)} minutes left)", "TEST RUNNER")
                break

        try:
            chaos.stop_random_single_action_and_repair()
            
            if consumer_count > 0:
                consumer_manager.stop_random_consumer_actions()
            
            if include_chaos:
                chaos_thread.join(30)

            if include_con_actions:
                consumer_action_thread.join(30)
        except Exception as e:
            console_out("Failed to stop chaos cleanly: " + str(e), "TEST RUNNER")

        if publisher_count > 0:
            publisher.stop_publishing()

        if consumer_count > 0:
            console_out("Resuming consumers", "TEST RUNNER")
            consumer_manager.resume_all_consumers()
               
            console_out("Starting grace period for consumer to catch up", "TEST RUNNER")
            ctr = 0
            
            try:
                while ctr < grace_period_sec:
                    if publisher_count > 0 and msg_monitor.get_unique_count() >= publisher.get_pos_ack_count() and len(publisher.get_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                        break
                    time.sleep(1)
                    ctr += 1
            except KeyboardInterrupt:
                console_out("Grace period ended", "TEST RUNNER")

        console_out("RESULTS ----------------------------------------", "TEST RUNNER")
        if publisher_count > 0:
            confirmed_set = publisher.get_msg_set()
            not_consumed_msgs = confirmed_set.difference(msg_monitor.get_msg_set())
            console_out(f"Confirmed count: {publisher.get_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")
        else:
            not_consumed_msgs = set()
            console_out(f"Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")

        success = True
        if consumer_count > 0:
            if len(not_consumed_msgs) > 0:
                if sac_enabled:
                    console_out(f"FAILED TEST: Potential message loss or failure of consumers to consume or failure to promote Waiting to Active. Not consumed count: {len(not_consumed_msgs)}", "TEST RUNNER")
                else:
                    console_out(f"FAILED TEST: Potential message loss or failure of consumers to consume. Not consumed count: {len(not_consumed_msgs)}", "TEST RUNNER")
                failed_test_log.append(f"Test {test_number} FAILURE: Potential Message Loss. {len(not_consumed_msgs)} messsages.")
                failed_tests.add(test_number)
                
                lost_ctr = 0
                sorted_msgs = list(not_consumed_msgs)
                sorted_msgs.sort()
                for msg in sorted_msgs:
                    console_out(f"Lost? {msg}", "TEST RUNNER")
                    lost_ctr += 1
                    if lost_ctr > 500:
                        console_out("More than 500, truncated list", "TEST RUNNER")
                        break

                success = False

            if msg_monitor.get_out_of_order() == True:
                success = False
                console_out(f"FAILED TEST: Received out-of-order messages", "TEST RUNNER")
                failed_test_log.append(f"Test {test_number} FAILURE: Received out-of-order messages")
                failed_tests.add(test_number)

        if success:
            console_out("TEST OK", "TEST RUNNER")

        console_out("RESULTS END ------------------------------------", "TEST RUNNER")

        try:
            if consumer_count > 0:
                consumer_manager.stop_all_consumers()
            
            if publisher_count == 1:
                pub_thread.join(30)
            msg_monitor.stop_consuming()
            monitor_thread.join(30)
        except Exception as e:
            console_out_exception("Failed to clean up test correctly.", e, "TEST RUNNER")

        broker_manager.zip_log_files(test_name, test_number)
        console_out(f"TEST {str(test_number )} COMPLETE", "TEST RUNNER")

    console_out("", "TEST RUNNER")
    console_out("SUMMARY", "TEST RUNNER")
    console_out(f"OK {tests - len(failed_tests)} FAIL {len(failed_tests)}", "TEST RUNNER")
    for line in failed_test_log:
        console_out(line, "TEST RUNNER")

    console_out("TEST RUN COMPLETE", "TEST RUNNER")

if __name__ == '__main__':
    main()