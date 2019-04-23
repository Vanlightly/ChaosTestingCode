from KafkaProducer import KafkaProducer
from printer import console_out
import threading

class ProducerManager:
    def __init__(self, broker_manager, actor, topic_name):
        self.broker_manager = broker_manager
        self.producers = list()
        self.producer_threads = list()
        self.actor = actor
        self.topic_name = topic_name
    
    def add_producers(self, producer_count, test_number, acks_mode, in_flight_max, print_mod, sequence_count):
        for prod_id in range (1, producer_count+1):
            producer = KafkaProducer(test_number, prod_id, self.broker_manager, acks_mode, in_flight_max, print_mod)
            producer.create_producer(0, 0)
            producer.configure_as_sequence(sequence_count)
            self.producers.append(producer)

    def start_producers(self):
        for prod_id in range(1, len(self.producers)+1):
            prod_thread = threading.Thread(target=self.producers[prod_id-1].start_producing,args=(self.topic_name, 10000000))
            prod_thread.start()
            self.producer_threads.append(prod_thread)
            console_out(f"producer {prod_id} started", self.actor)

    def stop_all_producers(self):
        for producer in self.producers:
            producer.stop_producing()

        for prod_thread in self.producer_threads:
            prod_thread.join()

    def get_total_msg_set(self):
        all = set()
        for producer in self.producers:
            all = all.union(producer.get_msg_set())

        return all

    def get_total_pos_ack_count(self):
        total = 0
        for producer in self.producers:
            total += producer.get_pos_ack_count()

        return total

    def get_total_neg_ack_count(self):
        total = 0
        for producer in self.producers:
            total += producer.get_neg_ack_count()

        return total