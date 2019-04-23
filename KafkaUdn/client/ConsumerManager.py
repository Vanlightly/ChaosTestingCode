from BrokerManager import BrokerManager
from MessageMonitor import MessageMonitor
from KafkaConsumer import KafkaConsumer
from printer import console_out
import random
from random import shuffle
import time
import uuid
import threading

class ConsumerManager:
    def __init__(self, broker_manager, msg_monitor, actor, topic_name, group_id):
        self.consumers = list()
        self.consumer_threads = list()
        self.broker_manager = broker_manager
        self.msg_monitor = msg_monitor
        self.actor = actor
        self.stop_random = False
        self.topic_name = topic_name
        self.group_id = group_id

    def add_consumers(self, consumer_count, test_number):
        for con_id in range (1, consumer_count+1):
            consumer = KafkaConsumer(self.broker_manager, self.msg_monitor, con_id, test_number)
            consumer.create_consumer(self.group_id, self.topic_name)
            self.consumers.append(consumer)

    def start_consumers(self):
        for con_id in range(1, len(self.consumers)+1):
            con_thread = threading.Thread(target=self.consumers[con_id-1].start_consuming)
            con_thread.start()
            self.consumer_threads.append(con_thread)
            console_out(f"consumer {con_id} started", self.actor)

    def add_consumer_and_start_consumer(self, test_number):
        con_id = len(self.consumers)+1
        consumer = KafkaConsumer(self.broker_manager, self.msg_monitor, con_id, test_number)
        consumer.create_consumer(self.group_id, self.topic_name)
        self.consumers.append(consumer)
        con_thread = threading.Thread(target=consumer.start_consuming)
        con_thread.start()
        self.consumer_threads.append(con_thread)
        console_out(f"consumer {con_id} added and started", self.actor)

    def stop_and_remove_consumer(self):
        if len(self.consumers) > 0:
            console_out("Stopping consumer...", self.actor)
            self.consumers[0].stop_consuming()
            self.consumer_threads[0].join()
            self.consumers.remove(self.consumers[0])
            self.consumer_threads.remove(self.consumer_threads[0])
            console_out("Consumer removed", self.actor)

    def do_consumer_action(self):
        con_indexes = [i for i in range(len(self.consumers))]
        shuffle(con_indexes)

        # for 3 consumers, do an action on 1
        # for 5 consumers, do an action of 2 etc etc
        actions_count = int(len(self.consumers)/2)
        for i in range(actions_count):
            self.do_single_consumer_action(con_indexes[i])

    def do_single_consumer_action(self, con_index):
        con = self.consumers[con_index]
        if con.terminate == True:
            console_out(f"Starting consumer {con_index+1}", self.actor)
            con.create_consumer(self.group_id, self.topic_name)
            self.consumer_threads[con_index] = threading.Thread(target=con.start_consuming)
            self.consumer_threads[con_index].start()
        else:
            console_out(f"Stopping consumer {con_index+1}", self.actor)
            try:
                con.stop_consuming()
                self.consumer_threads[con_index].join()
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:{1!r}"
                message = template.format(type(e).__name__, e.args)
                console_out(f"Failed to stop consumer correctly: {message}", self.actor)

    def get_running_consumer_count(self):
        running_cons = 0
        for con in self.consumers:
            if con.terminate == False:
                running_cons += 1

        return running_cons

    def resume_all_consumers(self):
        for con_index in range(0, len(self.consumers)):
            if self.consumers[con_index].terminate == True:
                console_out(f"Starting consumer {con_index+1}", self.actor)
                self.consumers[con_index].create_consumer(self.group_id, self.topic_name)
                self.consumer_threads[con_index] = threading.Thread(target=self.consumers[con_index].start_consuming)
                self.consumer_threads[con_index].start()

    def stop_all_consumers(self):
        for con in self.consumers:
            con.stop_consuming()

        for con_thread in self.consumer_threads:
            con_thread.join()

    def start_random_consumer_actions(self, min_seconds_interval, max_seconds_interval):
        while self.stop_random == False:
            wait_sec = random.randint(min_seconds_interval, max_seconds_interval)
            console_out(f"Will execute consumer action in {wait_sec} seconds", self.actor)
            self.wait_for(wait_sec)

            if self.stop_random == False:
                self.do_consumer_action()

    def stop_random_consumer_actions(self):
        self.stop_random = True

    def wait_for(self, seconds):
        ctr = 0
        while self.stop_random == False and ctr < seconds:
            ctr += 1
            time.sleep(1)