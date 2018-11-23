#!/usr/bin/env python
import pika
from pika import spec

class SyncPublisher:
    connection = None
    channel = None
    exchange_name = ""

    def connect(self, node):
        credentials = pika.PlainCredentials('jack', 'jack')
        parameters = pika.ConnectionParameters(node,
                                            5672,
                                            '/',
                                            credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()

    def declare(self, exchange_name):
        self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
        self.exchange_name = exchange_name
    
    def publish(self, num):
        success = self.channel.basic_publish(exchange=self.exchange_name,
                      routing_key="rk",
                      body=str(num))

        if success == False:
            print("Delivery failed")
                    
    def disconnect(self):
        self.connection.close()