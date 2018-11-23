import pika
from pika import spec
import sys
import time
import subprocess
import datetime
import uuid
import random

class RabbitPublisher(object):
    
    def __init__(self, node_count, connect_node):
        
        self._connection = None
        self._channel = None
        self._stopping = False

        self.message_type = ""
        self.exchange = ""   
        self.routing_key = ""
        self.count = 0
        self.state_count = 0
        self.dup_rate = 0.0
        self.total = 0
        self.expected = 0

        # message tracking
        self.last_ack_time = datetime.datetime.now()
        self.last_ack = 0
        self.seq_no = 0
        self.curr_pos = 0
        self.pending_messages = list()
        self.pending_acks = list()
        self.pos_acks = 0
        self.neg_acks = 0
        self.undeliverable = 0
        self.state_index = 0
        self.states = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        self.val = 1

        # nodes and ips
        self.curr_node = 0
        self.connect_node = connect_node
        self.node_count = node_count

        self.node_names = []
        for i in range(1, node_count+1):
            self.node_names.append(f"rabbitmq{i}")
        
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
        if self.curr_node > self.node_count:
            self.curr_node = 0

    def connect(self):
        print("Attempting to connect to " + self.nodes[self.curr_node])
        parameters = pika.URLParameters('amqp://jack:jack@' + self.nodes[self.curr_node] + ':5672/%2F')
        return pika.SelectConnection(parameters,
                                     on_open_callback=self.on_connection_open,
                                     on_open_error_callback=self.on_connection_open_error,
                                     on_close_callback=self.on_connection_closed)

    def on_connection_open(self, unused_connection):
        print(f'Connection opened: {unused_connection}')
        self.open_channel()

    def on_connection_open_error(self, unused_connection, err):
        print('Connection open failed, reopening in 5 seconds: %s', err)
        self.next_node()
        self._connection.ioloop.add_timeout(5, self._connection.ioloop.stop)

    def on_connection_closed(self, connection, reason_code, reason_text):
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()
        else:
            print(f"Connection closed. Code: {reason_code} Text: {reason_text}. Reopening in 5 seconds.")
            self.next_node()
            self._connection.ioloop.add_timeout(5, self._connection.ioloop.stop)

    def open_channel(self):
        #print('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self._channel = channel
        self.add_on_channel_close_callback()
        print('Channel opened, publishing to commence')
        # if the connection was lost then any previously tracked messages will not be acked
        
        pending_count = len(self.pending_messages)
        if pending_count > 0:
            print(f"{pending_count} messages were pending acknowledgement. Adjusted expected count to: {self.expected - pending_count}")
            self.expected = self.expected - pending_count
            self.pending_messages.clear()

        self.seq_no = 0
        self.start_publishing()

    def add_on_channel_close_callback(self):
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        print(f"Channel {channel} was closed. Code: {reply_code} Text: {reply_text}")
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def repeat_to_length(self, string_to_expand, length):
        return (string_to_expand * (int(length/len(string_to_expand))+1))[:length]

    def start_publishing(self):
        self.enable_delivery_confirmations()
        rk = self.routing_key
        body = ""
        large_msg = self.repeat_to_length("1234567890", 1000)
        
        while self.curr_pos < self.total:
            if self._channel.is_open:
                if self.curr_pos % 1000 == 0:
                    if len(self.pending_messages) > 10000:
                        #print("Reached in-flight limit, pausing publishing for 2 seconds")
                        if self._channel.is_open:
                            print(f"{len(self.pending_messages)} pending messages")
                            self._connection.add_timeout(2, self.start_publishing)
                            break

                self.curr_pos += 1
                self.seq_no += 1
                corr_id = str(uuid.uuid4())
                
                if self.message_type == "partitioned-sequence":
                    rk = self.states[self.state_index]
                    body = f"{self.states[self.state_index]}={self.val}"
                elif self.message_type == "sequence":
                    body = f"{self.states[self.state_index]}={self.val}"
                elif self.message_type == "large-msgs":
                    body = large_msg
                else:
                    body = "hello"
                
                self._channel.basic_publish(exchange=self.exchange, 
                                    routing_key=rk,
                                    body=body,
                                    mandatory=True,
                                    properties=pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=2,
                                                            correlation_id=corr_id))

                # potentially send a duplicate if enabled
                if self.dup_rate > 0:
                    if random.uniform(0, 1) < self.dup_rate:
                        self._channel.basic_publish(exchange=self.exchange, 
                                    routing_key=self.routing_key,
                                    body=body,
                                    mandatory=True,
                                    properties=pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=2,
                                                            correlation_id=corr_id))

                self.pending_messages.append(self.seq_no)

                self.state_index += 1
                if self.state_index == self.state_count:
                    self.state_index = 0
                    self.val += 1
                
            else:
                print("Channel closed, ceasing publishing")
                break

    def enable_delivery_confirmations(self):
        self._channel.confirm_delivery(callback=self.on_delivery_confirmation)
        self._channel.add_on_return_callback(callback=self.on_undeliverable)

    def on_undeliverable(self, channel, method, properties, body):
        body_str = str(body, "utf-8")
        print(f"Message could not be delivered: {body_str}")
        self.undeliverable += 1

    def on_delivery_confirmation(self, frame):
        if isinstance(frame.method, spec.Basic.Ack) or isinstance(frame.method, spec.Basic.Nack):
            if frame.method.multiple == True:
                acks = 0
                messages_to_remove = [item for item in self.pending_messages if item <= frame.method.delivery_tag]
                for val in messages_to_remove:
                    try:
                        self.pending_messages.remove(val)
                    except:
                        print(f"Could not remove multiple flag message: {val}")
                    acks += 1
            else:
                try:
                    self.pending_messages.remove(frame.method.delivery_tag) 
                except:
                    print(f"Could not remove non-multiple flag message: {frame.method.delivery_tag}")
                acks = 1

        if isinstance(frame.method, spec.Basic.Ack):
            self.pos_acks += acks
        elif isinstance(frame.method, spec.Basic.Nack):
            self.neg_acks += acks
        elif isinstance(frame.method, spec.Basic.Return):
            print("Undeliverable message")
        
        curr_ack = int((self.pos_acks + self.neg_acks) / 10000)
        if curr_ack > self.last_ack:
            print(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable}")
            self.last_ack = curr_ack

        if (self.pos_acks + self.neg_acks) >= self.expected:
            print(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable}")
            self.stop()
            exit(0)

    def publish_direct(self, queue, count, state_count, dup_rate, message_type):
        self.publish("", queue, count, state_count, dup_rate, message_type)
    
    def publish(self, exchange, routing_key, count, state_count, dup_rate, message_type):
        print(f"Will publish to exchange {exchange} and routing key {routing_key}")
        self.exchange = exchange
        self.routing_key = routing_key
        self.count = count
        self.state_count = state_count
        self.dup_rate = dup_rate
        self.total = count * state_count
        self.expected = self.total
        self.message_type = message_type

        if self.message_type == "partitioned-sequence":
            print("Routing key is ignored with the sequence type")

        if self.state_count > 10:
            print("Key count limit is 10")
            exit(1)

        allowed_types = ["partitioned-sequence", "sequence", "large-msgs", "hello"]
        if self.message_type not in allowed_types:
            print(f"Valid message types are: {allowed_types}")
            exit(1)

        while not self._stopping:
            self._connection = None
            
            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                if (self._connection is not None and
                        not self._connection.is_closed):
                    # Finish closing
                    self._connection.ioloop.start()

        #print('Stopped')

    def stop(self):
        #print('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        if self._channel is not None:
            #print('Closing the channel')
            self._channel.close()

    def close_connection(self):
        if self._connection is not None:
            #print('Closing connection')
            self._connection.close()
