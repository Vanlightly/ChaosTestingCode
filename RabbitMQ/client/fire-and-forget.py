#!/usr/bin/env python
import pika
import sys
import time

# args:
# 1 count
# 2 port

node_names = ['rabbitmq1', 'rabbitmq2', 'rabbitmq3']
nodes = ['172.17.0.2', '172.17.0.3', '172.17.0.4']

def get_node_ip(node_name):
    index = 0
    for node in node_names:
        if node == node_name:
            return nodes[index]

        index +=1

    return -1

def get_node_index(node_name):
    index = 0
    for node in node_names:
        if node == node_name:
            return index

        index +=1

    return -1

def connect():
    curr_node = get_node_index(sys.argv[1])
    while True:
        try:
            credentials = pika.credentials.PlainCredentials('jack', 'jack')
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=nodes[curr_node], port=5672, credentials=credentials))
            channel = connection.channel()
            print("Connected to " + nodes[curr_node])
            return channel
        except:
            curr_node += 1
            if curr_node > 2:
                print("Could not connect. Trying again in 5 seconds")
                time.sleep(5)
                curr_node  = 0

channel = connect()

count = int(sys.argv[2])
queue = sys.argv[3]
success = 0
fail = 0
sent = 0

for x in range(count):
    try:
        if channel.basic_publish(exchange='',
                            routing_key=queue,
                            body='Hello World!',
                            properties=pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=2)):
            success += 1       
        else:
            fail += 1

        sent += 1
        if sent % 10000 == 0:
            print("Success: " + str(success) + " Failed: " + str(fail))
    except pika.exceptions.ConnectionClosed:
        print("Connection closed.")
        time.sleep(5)
        channel = connect()
        count += 1 # retry it

time.sleep(5)
print("Sent " + str(sent) + " messages")
res = channel.queue_declare(queue=queue, durable=True)
message_count = res.method.message_count
print(str(message_count) + " messages in the queue")
print(str(success - message_count) + " messages lost")
