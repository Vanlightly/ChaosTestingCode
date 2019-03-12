#!/usr/bin/env python
import pika
from pika import spec
import time
import random
import subprocess

from printer import console_out

class MultiTopicConsumer:
    
    def __init__(self, consumer_id, node_names, check_ordering, print_mod, connect_node):
        self.node_names = node_names
        self.connection = None
        self.channel = None
        self.queue_name = ""
        self.check_ordering = check_ordering
        self.keys = dict()
        self.print_mod = print_mod
        self.receive_ctr = 0
        self.out_of_order = False;
        self.terminate = False
        self.consumer_id = consumer_id
        self.connected_node = connect_node
        self.msg_set = set()

        self.nodes = list()
        for node_name in self.node_names:
            self.nodes.append(self.get_node_ip(node_name))

        self.curr_node = self.get_node_index(connect_node)
    
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
        self.curr_node += 1
        if self.curr_node >= len(self.node_names):
            self.curr_node = 0

    def get_actor(self):
        return f"CONSUMER({self.consumer_id})->{self.connected_node}"

    def get_received_count(self):
        return self.receive_ctr;

    def received_out_of_order(self):
        return self.out_of_order;

    def connect(self):
        self.connected_node = self.nodes[self.curr_node]
        credentials = pika.PlainCredentials('jack', 'jack')
        parameters = pika.ConnectionParameters(self.connected_node,
                                            5672,
                                            '/',
                                            credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=10)

    def declare(self, queue_name, exchanges):
        self.channel.queue_declare(queue=queue_name, durable=True)

        for exchange_name in exchanges:
            self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
            self.channel.queue_bind(queue=queue_name, exchange=exchange_name)

        self.queue_name = queue_name

    def set_queue(self, queue_name):
        self.queue_name = queue_name
    
    def check_order(self, message_body, redelivered):
        body_str = str(message_body, "utf-8")
        parts = body_str.split('=')
        key = parts[0]
        curr_value = int(parts[1])

        if body_str in self.msg_set:
            duplicate = f"DUPLICATE"
            is_dup = True
        else:
            duplicate = ""
            is_dup = False

        if redelivered:
            redelivered_str = "REDELIVERED"
        else:
            redelivered_str = ""

        self.msg_set.add(body_str)

        if key in self.keys:
            last_value = self.keys[key]
            
            if last_value + 1 < curr_value:
                jump = curr_value - last_value
                console_out(f"{message_body} Jump forward {jump} {duplicate} {redelivered_str}", self.get_actor())
            elif last_value > curr_value:
                jump = last_value - curr_value
                console_out(f"{message_body} Jump back {jump} {duplicate} {redelivered_str}", self.get_actor())
                if is_dup == False:
                    self.out_of_order = True
            elif self.receive_ctr % self.print_mod == 0:
                console_out(f"Sample msg: {message_body} {duplicate} {redelivered_str}", self.get_actor())
            elif is_dup or redelivered:
                console_out(f"Msg: {message_body} {duplicate} {redelivered_str}", self.get_actor())
        else:
            if curr_value == 1:
                console_out(f"Latest msg: {message_body} {duplicate} {redelivered_str}", self.get_actor())
            else:
                console_out(f"{message_body} Jump forward {curr_value} {duplicate} {redelivered_str}", self.get_actor())
                self.out_of_order = True
        
        self.keys[key] = curr_value

    def callback(self, ch, method, properties, body):
        ch.basic_ack(delivery_tag = method.delivery_tag)
        self.receive_ctr += 1

        if self.check_ordering:
            self.check_order(body, method.redelivered)
        elif self.receive_ctr % self.print_mod == 0:
            console_out(f"{body}", self.get_actor())

    def disconnect(self):
        try:
            if self.connection is not None and self.connection.is_open:
                self.connection.close()

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
        self.connect()

    def consume(self):
        while True:
            try:
                if self.terminate == True:
                    break

                if self.connection is None or self.connection.is_closed:
                    self.reconnect()

                console_out(f"Consuming queue: {self.queue_name}", self.get_actor())
                self.channel.basic_consume(self.callback,
                            queue=self.queue_name,
                            no_ack=False)

                self.channel.start_consuming()
            except KeyboardInterrupt:
                console_out("Stopping consumption and closing the connection", self.get_actor())
                self.channel.stop_consuming()
                self.connection.close()
                console_out("Connection closed", self.get_actor())
                break
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
        self.connection.close()

    def get_msg_set(self):
        return self.msg_set
        