#!/usr/bin/env python
import pika
from pika import spec
import time
import random

class MultiTopicConsumer:
    connection = None
    channel = None
    queue_name = ""
    processing_ms_min = 0
    processing_ms_max = 0

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
    
    def callback(self, ch, method, properties, body):
        ch.basic_ack(delivery_tag = method.delivery_tag)
        print(f"{body}")
        # if self.processing_ms_max > 0:
        #     proc_sec = random.randint(self.processing_ms_min, self.processing_ms_max) / 1000.0
        #     print(f"Sleeping: {proc_sec} seconds")
        #     time.sleep(proc_sec)

    def consume(self, processing_ms_min, processing_ms_max):
        print(f"Consuming queue: {self.queue_name}")
        self.channel.basic_consume(self.callback,
                      queue=self.queue_name,
                      no_ack=False)

        self.processing_ms_min = processing_ms_min
        self.processing_ms_max = processing_ms_max

        try:
            self.channel.start_consuming()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message) 
                    
    def disconnect(self):
        self.connection.close()