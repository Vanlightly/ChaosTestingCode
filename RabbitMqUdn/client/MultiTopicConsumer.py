#!/usr/bin/env python
import pika
from pika import spec
import time
import random
import subprocess

from printer import console_out, console_out_exception

class MultiTopicConsumer:
    
    def __init__(self, consumer_id, test_number, broker_manager, message_monitor, prefetch):
        self.broker_manager = broker_manager
        self.connection = None
        self.channel = None
        self.queue_name = ""
        self.prefetch = prefetch
        self.message_monitor = message_monitor
        self.terminate = False
        self.hard_close = False
        self.consumer_id = f"C{consumer_id}"
        self.test_number = test_number
        self.connected_node = broker_manager.get_current_node(self.consumer_id)
        self.consumer_tag = ""
        self.actor = "-"
        self.last_msg = ""
        self.set_actor()
    
    def get_consumer_id(self):
        return self.consumer_id

    def set_actor(self):
        self.actor = f"CONSUMER (Test:{self.test_number} Id:{self.consumer_id})->{self.connected_node}"
    
    def get_actor(self):
        return self.actor

    def connect(self):
        try:
            self.connected_node = self.broker_manager.get_current_node(self.consumer_id)
            ip = self.broker_manager.get_node_ip(self.connected_node)
            console_out(f"Connecting to {self.connected_node}", self.get_actor())
            credentials = pika.PlainCredentials('jack', 'jack')
            parameters = pika.ConnectionParameters(ip,
                                                5672,
                                                '/',
                                                credentials)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            if self.prefetch > 0:
                self.channel.basic_qos(prefetch_count=self.prefetch)

            return True
        except Exception as e:
            console_out_exception("Failed trying to connect.", e, self.get_actor())
            return False 

    def declare(self, queue_name, exchanges):
        self.channel.queue_declare(queue=queue_name, durable=True)

        for exchange_name in exchanges:
            self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
            self.channel.queue_bind(queue=queue_name, exchange=exchange_name)

        self.queue_name = queue_name

    def set_queue(self, queue_name):
        self.queue_name = queue_name
    
    def callback(self, ch, method, properties, body):
        if not self.terminate:
            self.last_msg = body
            self.message_monitor.append(body, self.consumer_tag, self.consumer_id, self.get_actor(), method.redelivered)
            ch.basic_ack(delivery_tag = method.delivery_tag)
            

    def disconnect(self):
        try:
            if not self.hard_close and self.channel is not None and self.channel.is_open:
                self.channel.stop_consuming()
                console_out(f"Cancelled consumer", self.get_actor())
                self.connection.sleep(2)

            if self.connection is not None and self.connection.is_open:
                self.connection.close()
                console_out(f"Closed connection", self.get_actor())

            return True
        except AttributeError:
            console_out(f"Closed connection (with internal pika attribute error)", self.get_actor())
        except TypeError:
            console_out(f"Closed connection (with internal pika type error)", self.get_actor())
        except pika.exceptions.ConnectionWrongStateError:
            console_out(f"Cannot close connection, already closed", self.get_actor())
        except pika.exceptions.StreamLostError:
            console_out(f"Closed connection (stream lost)", self.get_actor())
        except Exception as e:
            console_out_exception("Failed trying to disconnect.", e, self.get_actor())
            return False
        
    def reconnect(self):
        self.connection = None
        self.channel = None
        console_out("Connection is closed. Opening new connection", self.get_actor())
        self.broker_manager.next_node(self.consumer_id)
        return self.connect()

    def wait_for(self, seconds):
        start = time.time()
        
        while self.terminate == False:
            if time.time() - start > seconds:
                break
            time.sleep(0.01)

    def consume(self):
        self.terminate = False
        self.hard_close = False
        self.last_msg = ""
        while True:
            try:
                if self.terminate == True:
                    break

                if self.connection is None or self.connection.is_closed or self.channel is None or self.channel.is_closed:
                    if self.reconnect() == False:
                        self.wait_for(5)
                        continue

                self.consumer_tag = self.channel.basic_consume(self.queue_name, self.callback)
                
                console_out(f"Consuming queue: {self.queue_name} with consumer tag: {self.consumer_tag}", self.get_actor())

                self.set_actor()
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosed as e:
                if self.terminate == True:
                    break
                
                console_out_exception(f"Connection was closed. Last msg acked: {self.last_msg}", e, self.get_actor())
                self.wait_for(5)
                continue
            except pika.exceptions.AMQPChannelError as e:
                if self.terminate == True:
                    break

                console_out_exception(f"Caught a channel error. Last msg acked: {self.last_msg}", e, self.get_actor())
                self.wait_for(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True
                    console_out("Aborting consumer", self.get_actor())
                    break
            except pika.exceptions.AMQPConnectionError as e:
                if self.terminate == True:
                    break

                console_out_exception(f"Connection error. Last msg acked: {self.last_msg}", e, self.get_actor())
                self.wait_for(5)
                continue
            except Exception as e:
                if self.terminate == True:
                    break
                
                console_out_exception(f"Unexpected error. Last msg acked: {self.last_msg}", e, self.get_actor())                
                self.wait_for(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True
                    console_out("Aborting consumer", self.get_actor())
                    break

    def stop_consuming(self):
        self.terminate = True
        if self.last_msg != "":
            console_out(f"Requested to stop. Last msg acked: {self.last_msg}", self.get_actor())
        else:
            console_out(f"Requested to stop.", self.get_actor())
        self.disconnect()

    def perform_hard_close(self):
        self.terminate = True
        self.hard_close = True
        if self.last_msg != "":
            console_out(f"Requested to hard close. Last msg acked: {self.last_msg}", self.get_actor())
        else:
            console_out(f"Requested to hard close.", self.get_actor())
        self.disconnect()
        