#!/usr/bin/env python
import pika
import sys
import time
import subprocess

queue = sys.argv[1]
nodes = list()

def connect():
    curr_node = 0
    while True:
        try:
            credentials = pika.credentials.PlainCredentials('jack', 'jack')
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=nodes[curr_node], port=5672, credentials=credentials))
            channel = connection.channel()
            return channel
        except:
            curr_node += 1
            if curr_node > 2:
                print("Could not connect. Trying again in 5 seconds")
                time.sleep(5)
                curr_node  = 0

def get_node_ip(node_name):
    bash_command = "bash ../cluster/get-node-ip.sh " + node_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

for node_name in node_names:
    nodes.append(get_node_ip(node_name))

channel = connect()

qRes = channel.queue_declare(queue=queue, durable=True)
print(qRes.method.message_count)
