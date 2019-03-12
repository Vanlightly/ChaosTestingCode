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


def get_live_nodes():
    bash_command = "bash ../cluster/list-live-nodes.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    nodes = list()
    for node in nodes_line.split(' '):
        if node != '' and node.isspace() == False:
            nodes.append(node)

    return nodes

args = get_args(sys.argv)
connect_node = get_optional_arg(args, "--node", "rabbitmq1") #sys.argv[1]
queue = get_mandatory_arg(args, "--queue")
#exchanges = get_mandatory_arg(args, "--exchanges").split(',')

live_nodes = get_live_nodes()
consumer = MultiTopicConsumer("1", live_nodes, True, 100, connect_node)
consumer.connect()
#consumer.declare(queue, exchanges)
consumer.set_queue(queue)
consumer.consume()


