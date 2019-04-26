from BrokerManager import BrokerManager
from MessageMonitor import MessageMonitor
from MultiTopicConsumer import MultiTopicConsumer
from printer import console_out
import random
from random import shuffle
import time
import threading
from printer import console_out_exception

class ConsumerManager:
    def __init__(self, broker_manager, msg_monitor, actor):
        self.consumers = list()
        self.consumer_threads = list()
        self.broker_manager = broker_manager
        self.msg_monitor = msg_monitor
        self.actor = actor
        self.stop_random = False

    def add_consumers(self, consumer_count, test_number, queue_name):
        for con_id in range (1, consumer_count+1):
            consumer_node = self.broker_manager.get_init_node(con_id)
            console_out(f"Consumer {con_id} will first connect to {consumer_node}", self.actor)
            consumer = MultiTopicConsumer(con_id, test_number, self.broker_manager, self.msg_monitor, consumer_node)
            consumer.connect()
            consumer.set_queue(queue_name)

            self.consumers.append(consumer)

    def start_consumers(self):
        for con_id in range(1, len(self.consumers)+1):
            con_thread = threading.Thread(target=self.consumers[con_id-1].consume)
            con_thread.start()
            self.consumer_threads.append(con_thread)
            console_out(f"consumer {con_id} started", self.actor)

    def do_consumer_action(self):
        con_indexes = [i for i in range(len(self.consumers))]
        shuffle(con_indexes)

        # for 3 consumers, do an action on 1
        # for 5 consumers, do an action of 2 etc etc
        actions_count = max(1, int(len(self.consumers)/2))
        for i in range(actions_count):
            self.do_single_consumer_action(con_indexes[i])

    def do_single_consumer_action(self, con_index):
        con = self.consumers[con_index]
        if con.terminate == True:
            console_out(f"STARTING CONSUMER {con_index+1} --------------------------------------", self.actor)
            conn_ok = con.connect()
            if conn_ok:
                self.consumer_threads[con_index] = threading.Thread(target=con.consume)
                self.consumer_threads[con_index].start()
        else:
            console_out(f"STOPPING CONSUMER {con_index+1} --------------------------------------", self.actor)
            try:
                con.stop()
                self.consumer_threads[con_index].join(15)
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:{1!r}"
                message = template.format(type(e).__name__, e.args)
                console_out(f"Failed to stop consumer correctly: {message}", self.actor)

    def stop_start_consumers(self):
        con_indexes = [i for i in range(len(self.consumers))]
        shuffle(con_indexes)

        # for 3 consumers, do an action on 1
        # for 5 consumers, do an action of 2 etc etc
        actions_count = max(1, int(len(self.consumers)/2))
        for i in range(actions_count):
            self.stop_start_consumer(con_indexes[i])

    def stop_start_consumer(self, con_index):
        con = self.consumers[con_index]
        try:
            con.stop()
            self.consumer_threads[con_index].join(15)
            
            conn_ok = con.connect()
            if conn_ok:
                self.consumer_threads[con_index] = threading.Thread(target=con.consume)
                self.consumer_threads[con_index].start()
        except Exception as e:
            console_out_exception("Failed to stop/start consumer correctly", e, self.actor)

    def get_running_consumer_count(self):
        running_cons = 0
        for con in self.consumers:
            if con.terminate == False:
                running_cons += 1

        return running_cons

    def start_random_stop_starts(self, min_seconds_interval, max_seconds_interval):
        while self.stop_random == False:
            wait_sec = random.randint(min_seconds_interval, max_seconds_interval)
            console_out(f"Will execute stop/start consumer action in {wait_sec} seconds", self.actor)
            self.wait_for(wait_sec)

            if self.stop_random == False:
                try:
                    self.stop_start_consumers()
                except Exception as e:
                    console_out_exception("Failed stopping/starting consumers", e, self.actor)

    def resume_all_consumers(self):
        for con_index in range(0, len(self.consumers)):
            if self.consumers[con_index].terminate == True:
                console_out(f"Starting consumer {con_index+1}", self.actor)
                conn_ok = self.consumers[con_index].connect()
                if conn_ok:
                    self.consumer_threads[con_index] = threading.Thread(target=self.consumers[con_index].consume)
                    self.consumer_threads[con_index].start()

    def stop_all_consumers(self):
        for con in self.consumers:
            con.stop()

        for con_thread in self.consumer_threads:
            con_thread.join(15)

    def start_random_consumer_actions(self, min_seconds_interval, max_seconds_interval):
        while self.stop_random == False:
            wait_sec = random.randint(min_seconds_interval, max_seconds_interval)
            console_out(f"Will execute consumer action in {wait_sec} seconds", self.actor)
            self.wait_for(wait_sec)

            if self.stop_random == False:
                try:
                    self.do_consumer_action()
                except Exception as e:
                    console_out_exception("Failed performing consumer action", e, "TEST RUNNER")

    def stop_random_consumer_actions(self):
        self.stop_random = True

    def wait_for(self, seconds):
        ctr = 0
        while self.stop_random == False and ctr < seconds:
            ctr += 1
            time.sleep(1)