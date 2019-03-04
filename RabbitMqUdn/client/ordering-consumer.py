#!/usr/bin/env python
import pika
import sys
import time
import subprocess
import datetime
import threading
from command_args import get_args, get_mandatory_arg, get_optional_arg
from MultiTopicConsumer import MultiTopicConsumer

def get_node_ip(node_name):
    bash_command = "bash ../cluster/get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

args = get_args(sys.argv)
connect_node = get_optional_arg(args, "--node", "rabbitmq1") #sys.argv[1]
ip = get_node_ip(connect_node)

queue = get_mandatory_arg(args, "--queue")
exchanges = get_mandatory_arg(args, "--exchanges").split(',')

consumer = MultiTopicConsumer(True)
consumer.connect(ip)
consumer.declare(queue, exchanges)
consumer.consume()


