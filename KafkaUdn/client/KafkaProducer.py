import sys
import time
import subprocess
import datetime
import uuid
import random
import json

from confluent_kafka import Producer

from printer import console_out

class KafkaProducer(object):
    
    def __init__(self, test_number, producer_id, broker_manager, acks_mode, in_flight_limit, print_mod):
        
        self.broker_manager = broker_manager
        self.producer_id = f"PRODUCER(Test:{test_number} Id:P{producer_id})"
        self.producer = None
        self.acks_mode = acks_mode
        self.message_type = None
        self.terminate = False
        self.key_count = 1
        self.in_flight_limit = in_flight_limit
        self.print_mod = print_mod

        # message tracking
        self.curr_pos = 0
        self.pos_acks = 0
        self.neg_acks = 0
        self.key_index = 0
        self.keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        self.val = 1
        self.msg_set = set()
        self.pending_ack = set()

    def create_producer(self, retry_limit):
        self.producer = Producer({'bootstrap.servers': self.broker_manager.get_bootstrap_servers(),
                            'message.send.max.retries': retry_limit,
                            #'queue.buffering.max.ms': 100,
                            #'batch.num.messages': 1000,
                            #'stats_cb': my_stats_callback,
                            #'statistics.interval.ms': 100,
                            'default.topic.config': { 'request.required.acks': self.acks_mode }})

    def create_producer_with_buffering(self, retry_limit, buffering_max):
        self.producer = Producer({'bootstrap.servers': self.broker_manager.get_bootstrap_servers(),
                            'message.send.max.retries': retry_limit,
                            'queue.buffering.max.ms': buffering_max,
                            #'batch.num.messages': 1000,
                            #'stats_cb': my_stats_callback,
                            #'statistics.interval.ms': 100,
                            'default.topic.config': { 'request.required.acks': self.acks_mode }})

    def create_idempotent_producer(self, buffering_max):
        self.producer = Producer({'bootstrap.servers': self.broker_manager.get_bootstrap_servers(),
                            'message.send.max.retries': retry_limit,
                            'enable.idempotence': True,
                            'queue.buffering.max.ms': buffering_max,
                            #'batch.num.messages': 1000,
                            #'stats_cb': my_stats_callback,
                            #'statistics.interval.ms': 100,
                            'default.topic.config': { 'request.required.acks': self.acks_mode }
                        })

    def get_actor(self):
        return self.producer_id

    def delivery_report(self, err, msg):
        if self.terminate:
            return
        
        val = msg.value().decode("utf-8")
        self.pending_ack.remove(val)

        if err:
            self.neg_acks += 1
            #console_out(err, self.get_actor())
        else:
            self.pos_acks += 1
            self.msg_set.add(val)

        if (self.neg_acks + self.pos_acks) % self.print_mod == 0:
            console_out(f"Pos acks: {self.pos_acks} Neg acks:  {self.neg_acks}", self.get_actor())

    def configure_as_sequence(self, sequence_count):
        self.key_count = sequence_count
        self.message_type = "sequence"

    def configure_as_partitioned_sequence(self, sequence_count):
        self.key_count = sequence_count
        self.message_type = "partitioned-sequence"

    def start_producing(self, topic, msg_count):
        for msg_index in range(0, msg_count):
            if self.terminate:
                break

            self.producer.poll(0)

            body = None
            if self.message_type == "partitioned-sequence":
                topic = f"{topic}-{self.keys[self.key_index]}"
                body = f"{self.keys[self.key_index]}={self.val}"
            elif self.message_type == "sequence":
                body = f"{self.keys[self.key_index]}={self.val}"
            else:
                body = uuid.uuid4()

            while len(self.pending_ack) > self.in_flight_limit:
                time.sleep(0.2)
                if self.terminate:
                    break
                self.producer.poll(0)

            self.producer.produce(topic, value=body.encode('utf-8'),key=self.keys[self.key_index], callback=self.delivery_report)
            self.pending_ack.add(body)
            self.curr_pos += 1

            self.key_index += 1
            if self.key_index == self.key_count:
                self.key_index = 0
                self.val += 1

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks}", self.get_actor())

    def get_msg_set(self):
        return self.msg_set

    def get_pos_ack_count(self):
        return self.pos_acks
    
    def stop_producing(self):
        self.terminate = True
        self.print_final_count()