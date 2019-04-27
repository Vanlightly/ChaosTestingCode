#!/usr/bin/env python
import sys
import time
import threading
from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true, as_list
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
    new_cluster = is_true(get_optional_arg(args, "--new-cluster", "false"))
    if new_cluster:
        cluster_size = int(get_mandatory_arg(args, "--cluster-size"))
    else:
        cluster_size = int(get_optional_arg(args, "--cluster-size", "3"))

    rmq_version = get_optional_arg(args, "--rmq-version", "3.8")

    # queues and exchanges
    exchanges = as_list(get_optional_arg(args, "--exchanges", ""))
    queue_name = get_mandatory_arg(args, "--queue")
    queue_type = get_optional_arg(args, "--queue-type", "standard")
    rep_factor = int(get_optional_arg(args, "--rep-factor", "1"))
    sac_enabled = is_true(get_optional_arg(args, "--sac", "false"))

    if rmq_version == "3.7":
        if sac_enabled:
            console_out("Cannot use SAC mode with RabbitMQ 3.7", "TEST RUNNER")
            exit(1)
        
        if queue_type == "quorum":
            console_out("Cannot use quorum queues with RabbitMQ 3.7", "TEST RUNNER")
            exit(1)

    # publisher
    publisher_count = int(get_optional_arg(args, "--publishers", "1"))
    pub_mode = get_optional_arg(args, "--pub-mode", "direct")
    msg_mode = get_optional_arg(args, "--msg-mode", "sequence")
    count = int(get_mandatory_arg(args, "--msgs"))
    dup_rate = float(get_optional_arg(args, "--dup-rate", "0"))
    sequence_count = int(get_optional_arg(args, "--sequences", 1))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", 10))
    connect_node = get_optional_arg(args, "--connect-node", "rabbitmq1")

    # consumers
    consumer_count = int(get_optional_arg(args, "--consumers", "1"))
    prefetch = int(get_optional_arg(args, "--pre-fetch", "10"))
    analyze = is_true(get_optional_arg(args, "--analyze", "true"))

    
    print_mod = get_optional_arg(args, "--print-mod", in_flight_max * 5)

    broker_manager = BrokerManager()
    broker_manager.deploy(cluster_size, new_cluster, rmq_version)

    mgmt_node = broker_manager.get_random_init_node()
    queue_created = False
    while queue_created == False:    
        if sac_enabled:
            queue_created = broker_manager.create_sac_queue(mgmt_node, queue_name, rep_factor, queue_type)
        else:
            queue_created = broker_manager.create_queue(mgmt_node, queue_name, rep_factor, queue_type)
        if queue_created == False:
            time.sleep(5)

    broker_manager.declare_exchanges(queue_name, exchanges)

    time.sleep(10)

    if consumer_count > 0:
        msg_monitor = MessageMonitor(print_mod, analyze)
        consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER")
        consumer_manager.add_consumers(consumer_count, 1, queue_name, prefetch)

        monitor_thread = threading.Thread(target=msg_monitor.process_messages)
        monitor_thread.start()
        
        consumer_manager.start_consumers()

    if publisher_count > 0:
        pub_manager = PublisherManager(broker_manager, 1, "TEST RUNNER", publisher_count, connect_node, in_flight_max, print_mod)
        
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
            time.sleep(1)
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
    console_out("RESULTS END------------------------------------", "TEST RUNNER")

    try:
        consumer_manager.stop_all_consumers()
        msg_monitor.stop_consuming()
        monitor_thread.join()
    except Exception as e:
        console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")

    console_out(f"TEST 1 COMPLETE", "TEST RUNNER")


if __name__ == '__main__':
    main()


