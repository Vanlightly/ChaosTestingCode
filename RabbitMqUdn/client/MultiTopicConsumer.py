#!/usr/bin/env python
import pika
from pika import spec
import time
import random

class MultiTopicConsumer:
    
    def __init__(self, check_ordering):
        self.connection = None
        self.channel = None
        self.queue_name = ""
        self.check_ordering = check_ordering
        self.keys = dict()
    
    def connect(self, node):
        credentials = pika.PlainCredentials('jack', 'jack')
        parameters = pika.ConnectionParameters(node,
                                            5672,
                                            '/',
                                            credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def declare(self, queue_name, exchanges):
        self.channel.queue_declare(queue=queue_name, durable=True)

        for exchange_name in exchanges:
            self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
            self.channel.queue_bind(queue=queue_name, exchange=exchange_name)

        self.queue_name = queue_name

    def set_queue(self, queue_name):
        self.queue_name = queue_name
    
    def check_order(self, message_body):
        body_str = str(message_body, "utf-8")
        parts = body_str.split('=')
        key = parts[0]
        curr_value = int(parts[1])
        duplicate = "" # duplicate detection to be added later possibly

        if key in self.keys:
            last_value = self.keys[key]
            
            if last_value + 1 < curr_value:
                jump = curr_value - last_value
                print(f"{message_body} Jump forward {jump} {duplicate}")
            elif last_value > curr_value:
                jump = last_value - curr_value
                print(f"{message_body} Jump back {jump} {duplicate}")
            else:
                print(f"{message_body} {duplicate}")
        else:
            if curr_value == 1:
                print(f"{message_body} {duplicate}")
            else:
                print(f"{message_body} Jump forward {curr_value} {duplicate}")
        
        self.keys[key] = curr_value

    def callback(self, ch, method, properties, body):
        ch.basic_ack(delivery_tag = method.delivery_tag)

        if self.check_ordering:
            self.check_order(body)
        else:
            print(f"{body}")

    def consume(self):
        print(f"Consuming queue: {self.queue_name}")
        self.channel.basic_consume(self.callback,
                      queue=self.queue_name,
                      no_ack=False)

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("Stopping consumption and closing the connection")
            self.channel.stop_consuming()
            self.connection.close()
            print("Connection closed")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message)
            self.channel.stop_consuming()
            self.connection.close()