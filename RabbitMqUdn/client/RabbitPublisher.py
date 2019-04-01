import pika
from pika import spec
import sys
import time
import subprocess
import datetime
import uuid
import random

from printer import console_out

class RabbitPublisher(object):
    
    def __init__(self, publisher_id, node_names, connect_node, in_flight_limit, confirm_timeout_sec, print_mod):
        
        self._connection = None
        self._channel = None
        self._stopping = False

        self.publisher_id = publisher_id
        self.message_type = ""
        self.exchange = ""   
        self.exchanges = list()
        self.routing_key = ""
        self.count = 0
        self.sequence_count = 0
        self.dup_rate = 0.0
        self.total = 0
        self.expected = 0
        self.in_flight_limit = in_flight_limit
        self.confirm_timeout_sec = confirm_timeout_sec
        self.print_mod = print_mod

        # message tracking
        self.last_ack_time = datetime.datetime.now()
        self.last_ack = 0
        self.seq_no = 0
        self.curr_pos = 0
        self.pending_messages = list()
        self.pos_acks = 0
        self.neg_acks = 0
        self.undeliverable = 0
        self.no_acks = 0
        self.key_index = 0
        self.keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        self.val = 1
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.msg_set = set()
        self.msg_map = dict()
        
        # nodes and ips
        self.curr_node = 0
        self.connected_node = connect_node
        self.node_names = node_names
        self.nodes = list()

        for node_name in self.node_names:
            self.nodes.append(self.get_node_ip(node_name))

        self.curr_node = self.get_node_index(connect_node)
        self.actor = ""
        self.set_actor()

    def reset_ack_tracking(self):
        pending_count = len(self.pending_messages)
        if pending_count > 0:
            console_out(f"{pending_count} messages were pending acknowledgement. Adjusted expected count to: {self.expected - pending_count}", self.get_actor())
            self.expected = self.expected - pending_count
        
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.pending_messages.clear()

    def get_pos_ack_count(self):
        return self.pos_acks

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

    def set_actor(self):
        self.actor = f"{self.publisher_id}->{self.connected_node}"

    def get_actor(self):
        return self.actor

    def connect(self):
        self.connected_node = self.nodes[self.curr_node]
        self.set_actor()
        console_out("Attempting to connect to " + self.nodes[self.curr_node], self.get_actor())
        parameters = pika.URLParameters('amqp://jack:jack@' + self.nodes[self.curr_node] + ':5672/%2F')
        return pika.SelectConnection(parameters,
                                     on_open_callback=self.on_connection_open,
                                     on_open_error_callback=self.on_connection_open_error,
                                     on_close_callback=self.on_connection_closed,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        console_out(f'Connection opened: {unused_connection}', self.get_actor())
        self.open_channel()
        
    def on_connection_open_error(self, unused_connection, err):
        console_out(f'Connection open failed, reopening in 5 seconds: {err}', self.get_actor())
        self.next_node()
        self._connection.ioloop.add_timeout(5, self._connection.ioloop.stop)

    def on_connection_closed(self, connection, reason_code, reason_text):
        self.connected_node = "none"
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()                
        else:
            console_out(f"Connection closed. Code: {reason_code} Text: {reason_text}. Reopening in 5 seconds.", self.get_actor())
            self.next_node()
            self._connection.ioloop.add_timeout(5, self._connection.ioloop.stop)

    def open_channel(self):
        #print('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self._channel = channel
        self.add_on_channel_close_callback()
        console_out('Channel opened, publishing to commence', self.get_actor())
                
        self.reset_ack_tracking()
        self.seq_no = 0
        self.start_publishing()

    def add_on_channel_close_callback(self):
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        console_out(f"Channel {channel} was closed. Code: {reply_code} Text: {reply_text}", self.get_actor())
        self._channel = None
        if not self._stopping:
            if self._connection.is_open:    
                self._connection.close()

    def stop(self, full_stop):
        if not self._stopping:
            if full_stop:
                self._stopping = True

            self.close_connection()

            if not full_stop:
                console_out("Reopening a new connection in 10 seconds", self.get_actor())
                self.next_node()
                self._connection.ioloop.add_timeout(10, self._connection.ioloop.stop)

    def close_channel(self):
        if self._channel is not None:
            #print('Closing the channel')
            self._channel.close()

    def close_connection(self):
        self.connected_node = "none"
        if self._connection is not None:
            self._connection.close()

    def repeat_to_length(self, string_to_expand, length):
        return (string_to_expand * (int(length/len(string_to_expand))+1))[:length]

    def start_publishing(self):
        if self._channel == None or not self._channel.is_open:
            return

        self.enable_delivery_confirmations()
        rk = self.routing_key
        body = ""
        large_msg = self.repeat_to_length("1234567890", 1000)
        curr_exchange = 0
        send_to_exchange = None
        
        while not self._stopping and self.curr_pos < self.total:
            if self.waiting_for_acks_sec > self.confirm_timeout_sec:
                console_out("Confirms timed out. Removing pending confirms from tracking. Opening new connection.", self.get_actor())
                self.no_acks += len(self.pending_messages)
                self.reset_ack_tracking()
                self.stop(False) # close connection but do not shutdown
                break


            if self._channel.is_open:
                if self.curr_pos % 10 == 0:
                    if len(self.pending_messages) >= self.in_flight_limit:
                        
                        # if self.waiting_for_acks == False:
                        #     console_out("Reached in-flight limit, waiting for acks", self.get_actor())

                        self.waiting_for_acks = True
                        self.waiting_for_acks_sec += 1
                        if self._channel.is_open:
                            #print(f"{len(self.pending_messages)} pending messages")
                            self._connection.add_timeout(1, self.start_publishing)
                            break

                
                # if self.waiting_for_acks == True:
                #     console_out("Waiting over, received enough acks to publish again", self.get_actor())
                
                
                self.waiting_for_acks = False
                self.waiting_for_acks_sec = 0
                self.curr_pos += 1
                self.seq_no += 1
                corr_id = str(uuid.uuid4())
                
                if self.message_type == "partitioned-sequence":
                    rk = self.keys[self.key_index]
                    body = f"{self.keys[self.key_index]}={self.val}"
                    self.msg_map[self.seq_no] = body
                elif self.message_type == "sequence":
                    body = f"{self.keys[self.key_index]}={self.val}"
                    self.msg_map[self.seq_no] = body
                elif self.message_type == "large-msgs":
                    body = large_msg
                else:
                    body = "hello"
                
                if self.exchange != None:
                    send_to_exchange = self.exchange
                else:
                    if curr_exchange >= len(self.exchanges):
                        curr_exchange = 0
                    
                    send_to_exchange = self.exchanges[curr_exchange]
                    curr_exchange += 1
                    
                self._channel.basic_publish(exchange=send_to_exchange, 
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
                self.key_index += 1
                if self.key_index == self.sequence_count:
                    self.key_index = 0
                    self.val += 1
                
            else:
                console_out("Channel closed, ceasing publishing", self.get_actor())
                break

    def enable_delivery_confirmations(self):
        self._channel.confirm_delivery(callback=self.on_delivery_confirmation)
        self._channel.add_on_return_callback(callback=self.on_undeliverable)

    def on_undeliverable(self, channel, method, properties, body):
        body_str = str(body, "utf-8")
        self.undeliverable += 1
        if self.undeliverable % 100 == 0:
            console_out(f"{str(self.undeliverable)} messages could not be delivered", self.get_actor())

    def on_delivery_confirmation(self, frame):
        if isinstance(frame.method, spec.Basic.Ack) or isinstance(frame.method, spec.Basic.Nack):
            if frame.method.multiple == True:
                acks = 0
                messages_to_remove = [item for item in self.pending_messages if item <= frame.method.delivery_tag]
                for val in messages_to_remove:
                    try:
                        self.pending_messages.remove(val)
                        if isinstance(frame.method, spec.Basic.Ack) and val in self.msg_map:
                            self.msg_set.add(self.msg_map[val])
                    except:
                        console_out(f"Could not remove multiple flag message: {val}", self.get_actor())
                    acks += 1
            else:
                try:
                    self.pending_messages.remove(frame.method.delivery_tag) 
                    if isinstance(frame.method, spec.Basic.Ack) and frame.method.delivery_tag in self.msg_map:
                        self.msg_set.add(self.msg_map[frame.method.delivery_tag])
                except:
                    console_out(f"Could not remove non-multiple flag message: {frame.method.delivery_tag}", self.get_actor())
                acks = 1

        if isinstance(frame.method, spec.Basic.Ack):
            self.pos_acks += acks
        elif isinstance(frame.method, spec.Basic.Nack):
            self.neg_acks += acks
        elif isinstance(frame.method, spec.Basic.Return):
            console_out("Undeliverable message", self.get_actor())
        
        curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
        if curr_ack > self.last_ack:
            console_out(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self.last_ack = curr_ack

        if (self.pos_acks + self.neg_acks) >= self.expected:
            console_out(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self._stopping = True
            self.stop(True)
            

    def publish_direct(self, queue, count, sequence_count, dup_rate, message_type):
        self.publish("", queue, count, sequence_count, dup_rate, message_type)
    
    def publish_to_exchanges(self, exchanges, routing_key, count, sequence_count, dup_rate, message_type):
        self.exchanges = exchanges
        self.publish(None, routing_key, count, sequence_count, dup_rate, message_type)

    def publish(self, exchange, routing_key, count, sequence_count, dup_rate, message_type):
        self._stopping = False
        console_out(f"Will publish to exchange {exchange} and routing key {routing_key}", self.get_actor())
        self.exchange = exchange
        self.routing_key = routing_key
        self.count = count
        self.sequence_count = sequence_count
        self.dup_rate = dup_rate

        if count == -1:
            self.total = 100000000
        else:
            self.total = count * sequence_count

        self.expected = self.total
        self.message_type = message_type

        if self.message_type == "partitioned-sequence":
            console_out("Routing key is ignored with the sequence type", self.get_actor())

        if self.sequence_count > 10:
            console_out("Key count limit is 10", self.get_actor())
            exit(1)

        allowed_types = ["partitioned-sequence", "sequence", "large-msgs", "hello"]
        if self.message_type not in allowed_types:
            console_out(f"Valid message types are: {allowed_types}", self.get_actor())
            exit(1)

        while not self._stopping:
            self._connection = None

            self._connection = self.connect()
            self._connection.ioloop.start()

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())

    def get_msg_set(self):
        return self.msg_set