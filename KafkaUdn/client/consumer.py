#!/usr/bin/env python
import sys
import time
import subprocess
import random
import threading
import requests
import json

from command_args import get_args, get_mandatory_arg, get_optional_arg
from KafkaConsumer import KafkaConsumer
from printer import console_out
from MessageMonitor import MessageMonitor
from ConsumerManager import ConsumerManager
from BrokerManager import BrokerManager

def main():
    args = get_args(sys.argv)

    consumer_count = int(get_mandatory_arg(args, "--consumers"))
    topic = get_mandatory_arg(args, "--topic")
    print_mod = int(get_mandatory_arg(args, "--print-mod"))

    console_out(f"Starting...", "TEST RUNNER")
    console_out(f"Cluster status:", "TEST RUNNER")
    subprocess.call(["bash", "../cluster/cluster-status.sh"])
    
    broker_manager = BrokerManager()
    broker_manager.load_initial_nodes()
    initial_nodes = broker_manager.get_initial_nodes()
    console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")
        
    msg_monitor = MessageMonitor(print_mod)
    consumer_manager = ConsumerManager(broker_manager, msg_monitor, "TEST RUNNER", topic)
    consumer_manager.add_consumers(consumer_count, 1)

    monitor_thread = threading.Thread(target=msg_monitor.process_messages)
    monitor_thread.start()
    
    consumer_manager.start_consumers()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    try:
        consumer_manager.stop_all_consumers()
        msg_monitor.stop_consuming()
        monitor_thread.join()
    except Exception as e:
        console_out("Failed to clean up test correctly: " + str(e), "TEST RUNNER")
          
if __name__ == '__main__':
    main()