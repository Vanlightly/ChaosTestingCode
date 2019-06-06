#!/usr/bin/env python
import sys
import time
import threading
from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true, as_list, get_optional_arg_validated
from RabbitPublisher import RabbitPublisher
from BrokerManager import BrokerManager
from PublisherManager import PublisherManager
from MessageMonitor import MessageMonitor
from ConsumerManager import ConsumerManager
from printer import console_out


def main():
    print("publish-consume.py")
    args = get_args(sys.argv)

    # cluster
    new_cluster = is_true(get_optional_arg_validated(args, "--new-cluster", "false", ["true", "false"]))
    if new_cluster:
        cluster_size = int(get_mandatory_arg(args, "--cluster-size"))
    else:
        cluster_size = int(get_optional_arg(args, "--cluster-size", "3"))

    rmq_version = get_optional_arg_validated(args, "--rmq-version", "3.8-beta", ["3.7","3.8-beta","3.8-alpha"])

    # queues and exchanges
    exchanges = as_list(get_optional_arg(args, "--exchanges", ""))
    queue_name = get_mandatory_arg(args, "--queue")
    queue_type = get_optional_arg_validated(args, "--queue-type", "mirrored", ["mirrored", "quorum"])
    qq_max_length = int(get_optional_arg(args, "--qq-max-length", "0"))
    rep_factor = int(get_optional_arg(args, "--rep-factor", str(cluster_size)))
    sac_enabled = is_true(get_optional_arg_validated(args, "--sac", "false", ["true", "false"]))

    if rmq_version == "3.7":
        if sac_enabled:
            console_out("Cannot use SAC mode with RabbitMQ 3.7", "TEST RUNNER")
            exit(1)
        
        if queue_type == "quorum":
            console_out("Cannot use quorum queues with RabbitMQ 3.7", "TEST RUNNER")
            exit(1)

    # publisher
    publisher_count = int(get_optional_arg(args, "--publishers", "1"))
    pub_mode = get_optional_arg_validated(args, "--pub-mode", "direct", ["direct","exchange"])
    msg_mode = get_optional_arg_validated(args, "--msg-mode", "sequence", ["sequence", "partitioned-sequence","large-msgs","hello"])
    count = int(get_mandatory_arg(args, "--msgs"))
    dup_rate = float(get_optional_arg(args, "--dup-rate", "0"))
    sequence_count = int(get_optional_arg(args, "--sequences", 1))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    
    # consumers
    consumer_count = int(get_optional_arg(args, "--consumers", "1"))
    prefetch = int(get_optional_arg(args, "--pre-fetch", "10"))
    analyze = is_true(get_optional_arg_validated(args, "--analyze", "true", ["true", "false"]))

    
    print_mod = get_optional_arg(args, "--print-mod", in_flight_max * 5)

    broker_manager = BrokerManager()
    broker_manager.deploy(cluster_size, new_cluster, rmq_version, False)

    mgmt_node = broker_manager.get_random_init_node()
    queue_created = False
    while queue_created == False:    
        if queue_type == "mirrored":
            if sac_enabled:
                queue_created = broker_manager.create_standard_sac_queue(mgmt_node, queue_name, rep_factor)
            else:
                queue_created = broker_manager.create_standard_queue(mgmt_node, queue_name, rep_factor)
        elif queue_type == "quorum":
            if sac_enabled:
                queue_created = broker_manager.create_quorum_sac_queue(mgmt_node, queue_name, rep_factor, qq_max_length)
            else:
                queue_created = broker_manager.create_quorum_queue(mgmt_node, queue_name, rep_factor, qq_max_length)
        
        if queue_created == False:
            time.sleep(5)

    broker_manager.declare_exchanges(queue_name, exchanges)

    time.sleep(10)

    if consumer_count > 0:
        msg_monitor = MessageMonitor("pub-con", 1, print_mod, analyze, False)
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER", False)
        consumer_manager.add_consumers(consumer_count, 1, queue_name, prefetch)

        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        consumer_manager.start_consumers()

    if publisher_count > 0:
        pub_manager = PublisherManager(broker_manager, 1, "TEST RUNNER", publisher_count, in_flight_max, print_mod)
        
        if pub_mode == "direct":
            if msg_mode == "sequence":
                pub_manager.add_sequence_direct_publishers(queue_name, count, dup_rate, sequence_count)
            elif pub_mode == "partitioned-sequence":
                print("Cannot use partitioned sequence mode with direct mode")
                exit(1)
            elif pub_mode == "large-msgs":
                msg_size = int(get_mandatory_arg(args, "--msg-size"))
                pub_manager.add_large_msgs_direct_publishers(queue_name, count, dup_rate, msg_size)
            else:
                pub_manager.add_hello_msgs_direct_publishers(queue_name, count, dup_rate)
        elif pub_mode == "exchange":
            if len(exchanges) == 0:
                console_out("No exchanges provided", "TEST RUNNER")
                exit(1)

            if msg_mode == "sequence":
                pub_manager.add_sequence_to_exchanges_publishers(exchanges, "", count, dup_rate, sequence_count)
            elif msg_mode == "partitioned-sequence":
                pub_manager.add_partitioned_sequence_to_exchanges_publishers(exchanges, count, dup_rate, sequence_count)
            elif msg_mode == "large-msgs":
                msg_size = int(get_mandatory_arg(args, "--msg-size"))
                pub_manager.add_large_msgs_to_exchanges_publishers(exchanges, "", count, dup_rate, msg_size)
            else:
                pub_manager.add_hello_msgs_to_exchanges_publishers(exchanges, "", count, dup_rate)

        pub_manager.start_publishers()

    while True:
        try:
            console_out("Press + to add a consumer, - to remove a consumer, ! to remove the active consumer (SAC only)", "TEST_RUNNER")
            input_str = input()
            if input_str == "+":
                consumer_manager.add_consumer_and_start_consumer(1, queue_name, prefetch)
            elif input_str == "-":
                consumer_manager.stop_and_remove_oldest_consumer()
            else:
                consumer_manager.stop_and_remove_specfic_consumer(input_str)
        except KeyboardInterrupt:
            if publisher_count > 0:
                console_out("Stopping publishers. Starting grace period for consumers to catch up.", "TEST_RUNNER")
                pub_manager.stop_all_publishers()
            break

    if publisher_count > 0 and consumer_count > 0:
        try:
            ctr = 0
            while ctr < 300:
                if msg_monitor.get_unique_count() >= pub_manager.get_total_pos_ack_count() and len(pub_manager.get_total_msg_set().difference(msg_monitor.get_msg_set())) == 0:
                    break
                time.sleep(1)
                ctr += 1
        except KeyboardInterrupt:
            console_out("Grace period ended", "TEST RUNNER")

        confirmed_set = pub_manager.get_total_msg_set()
        lost_msgs = confirmed_set.difference(msg_monitor.get_msg_set())

        console_out("RESULTS------------------------------------", "TEST RUNNER")    
        console_out(f"Confirmed count: {pub_manager.get_total_pos_ack_count()} Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")
    
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
    
    elif publisher_count > 0:
        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Confirmed count: {pub_manager.get_total_pos_ack_count()}", "TEST RUNNER")
    elif consumer_count > 0:
        console_out("RESULTS------------------------------------", "TEST RUNNER")
        console_out(f"Received count: {msg_monitor.get_receive_count()} Unique received: {msg_monitor.get_unique_count()}", "TEST RUNNER")
    
    console_out("RESULTS END------------------------------------", "TEST RUNNER")

    try:
        if consumer_count > 0:
            consumer_manager.stop_all_consumers()
            msg_monitor.stop_consuming()
            monitor_thread.join(10)
    except Exception as e:
        console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

    console_out(f"TEST 1 COMPLETE", "TEST RUNNER")


if __name__ == '__main__':
    main()


