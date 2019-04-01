#!/usr/bin/env python
import pika
from pika import spec
import time
import random
import subprocess

from printer import console_out

class MultiTopicConsumer:
    
    def __init__(self, consumer_id, node_names, message_monitor, connect_node):
        self.node_names = node_names
        self.connection = None
        self.channel = None
        self.queue_name = ""
        self.message_monitor = message_monitor
        self.terminate = False
        self.consumer_id = consumer_id
        self.connected_node = connect_node
        self.consumer_tag = ""
        self.actor = "-"

        self.nodes = list()
        for node_name in self.node_names:
            self.nodes.append(self.get_node_ip(node_name))

        self.curr_node = self.get_node_index(connect_node)
        self.set_actor()
    
    def get_node_ip(self, node_name):
        bash_command = "bash ../cluster/get-node-ip.sh " + node_name
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ip = output.decode('ascii').replace('\n', '')
        return ip

    def get_node_index(self, node_name):
        index = 0
        for node in self.node_names:
            if node == node_name:
                return index

            index +=1

        return -1
        
    def next_node(self):
        new_node = self.curr_node
        while new_node == self.curr_node:
            new_node = random.randint(0, len(self.node_names)-1)

        self.curr_node = new_node

    def set_actor(self):
        self.actor = f"{self.consumer_id}->{self.connected_node}"
    
    def get_actor(self):
        return self.actor

    def connect(self):
        try:
            self.connected_node = self.nodes[self.curr_node]
            credentials = pika.PlainCredentials('jack', 'jack')
            parameters = pika.ConnectionParameters(self.connected_node,
                                                5672,
                                                '/',
                                                credentials)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=10)
            return True
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(e).__name__, e.args)
            console_out("Failed trying to connect. " + message, self.get_actor())
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
        if self.terminate == False:
            ch.basic_ack(delivery_tag = method.delivery_tag)
            self.message_monitor.append(body, self.consumer_tag, self.consumer_id, self.get_actor(), method.redelivered)
            

    def disconnect(self):
        try:
            if self.channel is not None and self.channel.is_open:
                self.channel.stop_consuming()

            if self.connection is not None and self.connection.is_open:
                self.connection.close()
                console_out(f"Closed connection", self.get_actor())

            return True
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(e).__name__, e.args)
            console_out("Failed trying to disconnect. " + message, self.get_actor())
            return False
        
    def reconnect(self):
        self.connection = None
        self.channel = None
        console_out("Connection is closed. Opening new connection", self.get_actor())
        self.next_node()
        return self.connect()

    def consume(self):
        self.terminate = False
        while True:
            try:
                if self.terminate == True:
                    break

                if self.connection is None or self.connection.is_closed or self.channel is None or self.channel.is_closed:
                    if self.reconnect() == False:
                        time.sleep(5)
                        continue

                self.consumer_tag = self.channel.basic_consume(self.callback,
                            queue=self.queue_name,
                            no_ack=False)
                
                console_out(f"Consuming queue: {self.queue_name} with consumer tag: {self.consumer_tag}", self.get_actor())

                self.set_actor()
                self.channel.start_consuming()
            # except KeyboardInterrupt:
            #     console_out("Stopping consumption and closing the connection", self.get_actor())
            #     self.channel.stop_consuming()
            #     self.connection.close()
            #     console_out("Connection closed", self.get_actor())
            #     break
            except pika.exceptions.ConnectionClosed:
                console_out("Connection was closed, retrying...", self.get_actor())
                time.sleep(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True;
                    console_out("Aborting consumer", self.get_actor())
                    break
            except pika.exceptions.AMQPChannelError as err:
                console_out("Caught a channel error: {}, stopping...".format(err), self.get_actor())
                time.sleep(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True;
                    console_out("Aborting consumer", self.get_actor())
                    break
            except pika.exceptions.AMQPConnectionError:
                console_out("Connection error, retrying...", self.get_actor())
                time.sleep(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True;
                    console_out("Aborting consumer", self.get_actor())
                    break
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                if "object has no attribute 'clear'" not in message: # seems like a bug in Pika
                    console_out(message, self.get_actor())
                time.sleep(5)
                if self.disconnect():
                    self.connected_node = "none"
                    continue
                else:
                    self.terminate = True;
                    console_out("Aborting consumer", self.get_actor())
                    break

    def stop(self):
        self.terminate = True
        self.disconnect()
        