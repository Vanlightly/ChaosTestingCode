import pika
from pika import spec
import sys
import time
import subprocess
import datetime
import uuid
import random
from itertools import permutations, combinations

from printer import console_out, console_out_exception

class RabbitPublisher(object):
    
    def __init__(self, publisher_id, test_number, broker_manager, in_flight_limit, confirm_timeout_sec, print_mod):
        
        self.broker_manager = broker_manager
        self._connection = None
        self._channel = None
        self._stopping = False
        self.is_blocked = False

        self.publisher_id = f"P{publisher_id}"
        self.test_number = test_number
        self.message_type = ""
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
        self.keys = list()
        self.val = 1
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.msg_set = set()
        self.undeliverable_set = set()
        self.msg_map = dict()
        
        # nodes and ips
        self.connected_node = broker_manager.get_current_node(self.publisher_id)
        self.actor = ""
        self.set_actor()
        self.create_keys()

    def create_keys(self):
        for i in range(1, 6):
            for k in list(combinations('abcde', i)):
                self.keys.append(f"{self.publisher_id}{''.join(k)}")

    def reset_ack_tracking(self):
        pending_count = len(self.pending_messages)
        if pending_count > 0:
            console_out(f"{pending_count} messages were pending acknowledgement. Adjusted expected count to: {self.expected - pending_count}", self.get_actor())
            self.expected = self.expected - pending_count
        
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.pending_messages.clear()

    def set_actor(self):
        pub_id = f"PUBLISHER(Test:{self.test_number} Id:{self.publisher_id})"
        self.actor = f"{pub_id}->{self.connected_node}"

    def get_actor(self):
        return self.actor

    def connect(self):
        self.connected_node = self.broker_manager.get_current_node(self.publisher_id)
        ip = self.broker_manager.get_node_ip(self.connected_node)
        self.set_actor()
        console_out(f"Attempting to connect to {self.connected_node} {ip}", self.get_actor())
        parameters = pika.URLParameters(f"amqp://jack:jack@{ip}:5672/%2F")
        return pika.SelectConnection(parameters,
                                     on_open_callback=self.on_connection_open,
                                     on_open_error_callback=self.on_connection_open_error,
                                     on_close_callback=self.on_connection_closed)

    def on_connection_open(self, unused_connection):
        console_out(f'Connection opened: {unused_connection}', self.get_actor())
        self.open_channel()
        self._connection.add_on_connection_blocked_callback(self.on_connnection_blocked)
        self._connection.add_on_connection_unblocked_callback(self.on_connnection_unblocked)
        
    def on_connnection_blocked(self, connection, method_frame):
        self.is_blocked = True
        console_out("Connection Blocked!!!", self.get_actor())

    def on_connnection_unblocked(self, connection, method_frame):
        self.is_blocked = False
        console_out("Connection Unblocked!!!", self.get_actor())


    def on_connection_open_error(self, unused_connection, err):
        console_out(f'Connection open failed, reopening in 5 seconds: {err}', self.get_actor())
        self.broker_manager.next_node(self.publisher_id)
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_closed(self, connection, reason):
        self.connected_node = "none"
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()                
        else:
            console_out(f"Connection closed. Reason: {reason}. Reopening in 5 seconds.", self.get_actor())
            self.broker_manager.next_node(self.publisher_id)
            self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def open_channel(self):
        #print('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self._channel = channel
        self.add_on_channel_close_callback()
        console_out('Channel opened, publishing to commence', self.get_actor())
                
        self.reset_ack_tracking()
        self.seq_no = 0
        self.send_messages()

    def add_on_channel_close_callback(self):
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        console_out(f"Channel {channel} was closed. Reason: {reason}", self.get_actor())
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
                self.broker_manager.next_node(self.publisher_id)
                self._connection.ioloop.call_later(10, self._connection.ioloop.stop)

    def close_channel(self):
        if self._channel is not None:
            #print('Closing the channel')
            self._channel.close()

    def close_connection(self):
        self.connected_node = "none"
        if self._connection is not None and self._connection.is_open:
            try:
                self._connection.close()
            except pika.execeptions.ConnectionWrongStateError:
                console_out("Cannot close connection, already closed", self.get_actor())
            except Exception as e:
                console_out_exception("Failed closing connection", e, self.get_actor())

    def repeat_to_length(self, string_to_expand, length):
        return (string_to_expand * (int(length/len(string_to_expand))+1))[:length]

    def send_messages(self):
        if self._channel == None or not self._channel.is_open:
            return

        self.is_blocked = False
        self.enable_delivery_confirmations()
        rk = self.routing_key
        body = ""
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
                
                if self.is_blocked:
                    self._connection.ioloop.call_later(1, self.send_messages)

                if self.curr_pos % 10 == 0:
                    if len(self.pending_messages) >= self.in_flight_limit:
                        
                        # if self.waiting_for_acks == False:
                        #     console_out("Reached in-flight limit, waiting for acks", self.get_actor())

                        self.waiting_for_acks = True
                        self.waiting_for_acks_sec += 1
                        if self._channel.is_open:
                            #print(f"{len(self.pending_messages)} pending messages")
                            self._connection.ioloop.call_later(1, self.send_messages)
                            break

                
                # if self.waiting_for_acks == True:
                #     console_out("Waiting over, received enough acks to publish again", self.get_actor())
                
                
                self.waitingreply_for_acks = False
                self.waiting_for_acks_sec = 0
                self.curr_pos += 1
                self.seq_no += 1
                corr_id = str(uuid.uuid4())
                
                if self.message_type == "partitioned-sequence":
                    rk = self.keys[self.key_index]
                    body = f"{self.keys[self.key_index]}={self.val}"
                elif self.message_type == "sequence":
                    body = f"{self.keys[self.key_index]}={self.val}"
                elif self.message_type == "large-msgs":
                    body = self.large_msg
                else:
                    body = "Hello there, how are you?"

                self.msg_map[self.seq_no] = body                
                body = f"{datetime.datetime.now()}|{body}"

                if len(self.exchanges) == 1:
                    curr_exchange = 0
                    send_to_exchange = self.exchanges[curr_exchange]
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
                        self._channel.basic_publish(exchange=send_to_exchange, 
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
        self._channel.confirm_delivery(self.on_delivery_confirmation)
        self._channel.add_on_return_callback(callback=self.on_undeliverable)

    def on_undeliverable(self, channel, method, properties, body):
        self.undeliverable += 1
        self.undeliverable_set.add(str(body, "utf-8"))
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
                
        curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
        if curr_ack > self.last_ack:
            console_out(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self.last_ack = curr_ack

        if (self.pos_acks + self.neg_acks) >= self.expected:
            console_out(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self._stopping = True
            self.stop(True)

    def configure_hello_msgs_direct(self, queue, count, dup_rate):
        self.routing_key = queue
        self.exchanges = [""]
        console_out(f"Will publish large messages to queue {queue}", self.get_actor())
        self.configure(count, dup_rate, "hello")

    def configure_hello_msgs_to_exchanges(self, exchanges, routing_key, count, dup_rate):
        self.exchanges = exchanges
        self.routing_key = routing_key
        console_out(f"Will publish hello msgs to exchanges {exchanges}", self.get_actor())
        self.configure(count, dup_rate, "hello")


    def configure_large_msgs_direct(self, queue, count, dup_rate, msg_size):
        self.large_msg = self.repeat_to_length("1234567890", msg_size)
        self.routing_key = queue
        self.exchanges = [""]
        console_out(f"Will publish large messages to queue {queue}", self.get_actor())
        self.configure(count, dup_rate, "large-msgs")

    def configure_large_msgs_to_exchanges(self, exchanges, routing_key, count, dup_rate, msg_size):
        self.large_msg = self.repeat_to_length("1234567890", msg_size)
        self.exchanges = exchanges
        self.routing_key = routing_key
        console_out(f"Will publish large msgs to exchanges {exchanges}", self.get_actor())
        self.configure(count, dup_rate, "large-msgs")

    def configure_sequence_direct(self, queue, count, dup_rate, sequence_count):
        self.sequence_count = sequence_count
        self.routing_key = queue
        self.exchanges = [""]
        console_out(f"Will publish {sequence_count} sequences to queue {queue}", self.get_actor())
        self.configure(count, dup_rate, "sequence")

    def configure_sequence_to_exchanges(self, exchanges, routing_key, count, dup_rate, sequence_count):
        self.exchanges = exchanges
        self.sequence_count = sequence_count
        self.routing_key = routing_key
        console_out(f"Will publish {sequence_count} sequences to exchanges {exchanges}", self.get_actor())
        self.configure(count, dup_rate, "sequence")

    def configure_partitioned_sequence_to_exchanges(self, exchanges, count, dup_rate, sequence_count):
        self.exchanges = exchanges
        self.sequence_count = sequence_count
        console_out(f"Will publish {sequence_count} partitioned sequences to exchanges {exchanges}", self.get_actor())
        self.configure(count, dup_rate, "partitioned-sequence")

    def configure(self, count, dup_rate, message_type):
        self._stopping = False
        self.count = count
        self.dup_rate = dup_rate

        if count == -1:
            self.total = 100000000
        else:
            self.total = count * max(self.sequence_count, 1)

        self.expected = self.total
        self.message_type = message_type

        if self.message_type == "partitioned-sequence" and self.routing_key != "":
            console_out("Routing key is ignored with the sequence type", self.get_actor())

        if self.sequence_count > 120:
            console_out("Key count limit is 120", self.get_actor())
            exit(1)

        allowed_types = ["partitioned-sequence", "sequence", "large-msgs", "hello"]
        if self.message_type not in allowed_types:
            console_out(f"Valid message types are: {allowed_types}", self.get_actor())
            exit(1)

    def start_publishing(self):
        while not self._stopping:
            self._connection = None

            self._connection = self.connect()
            self._connection.ioloop.start()

    def stop_publishing(self):
        self.stop(True)

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())

    def get_pos_ack_count(self):
        return self.pos_acks - self.undeliverable

    def get_neg_ack_count(self):
        return self.neg_acks

    def get_msg_set(self):
        return self.msg_set.difference(self.undeliverable_set)