#!/usr/bin/env python
import pika
import sys
import time

nodes = ['172.17.0.2', '172.17.0.3', '172.17.0.4']

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

channel = connect()

queue = sys.argv[1]
qRes = channel.queue_declare(queue=queue, durable=True)
print(qRes.method.message_count)
