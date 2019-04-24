from RabbitPublisher import RabbitPublisher
from printer import console_out
import threading

class PublisherManager:
    def __init__(self, broker_manager, test_number, actor, publisher_count, connect_node, in_flight_max, print_mod):
        self.broker_manager = broker_manager
        self.test_number = test_number
        self.publishers = list()
        self.publisher_threads = list()
        self.actor = actor
        self.publisher_count = publisher_count
        self.connect_node = connect_node
        self.in_flight_max = in_flight_max
        self.print_mod = print_mod

    def add_sequence_direct_publishers(self, queue_name, count, dup_rate, sequence_count):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_sequence_direct(queue_name, count, dup_rate, sequence_count)
            self.publishers.append(publisher)

    def add_large_msgs_direct_publishers(self, queue_name, count, dup_rate, msg_size):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_large_msgs_direct(queue_name, count, dup_rate, msg_size)
            self.publishers.append(publisher)

    def add_hello_msgs_direct_publishers(self, queue_name, count, dup_rate):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_hello_msgs_direct(queue_name, count, dup_rate)
            self.publishers.append(publisher)

    def add_sequence_to_exchanges_publishers(self, exchanges, routing_key, count, dup_rate, sequence_count):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_sequence_to_exchanges(exchanges, routing_key, count, dup_rate, sequence_count)
            self.publishers.append(publisher)

    def add_partitioned_sequence_to_exchanges_publishers(self, exchanges, count, dup_rate, sequence_count):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_partitioned_sequence_to_exchanges(exchanges, count, dup_rate, sequence_count)
            self.publishers.append(publisher)

    def add_large_msgs_to_exchanges_publishers(self, exchanges, routing_key, count, dup_rate, msg_size):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_large_msgs_to_exchanges(exchanges, routing_key, count, dup_rate, msg_size)
            self.publishers.append(publisher)

    def add_hello_msgs_to_exchanges_publishers(self, exchanges, routing_key, count, dup_rate):
        for pub_id in range (1, self.publisher_count+1):
            publisher = RabbitPublisher(pub_id, self.test_number, self.broker_manager, self.connect_node, self.in_flight_max, 120, self.print_mod)
            publisher.configure_hello_msgs_to_exchanges(exchanges, routing_key, count, dup_rate)
            self.publishers.append(publisher)

    def start_publishers(self):
        for prod_id in range(1, len(self.publishers)+1):
            pub_thread = threading.Thread(target=self.publishers[prod_id-1].start_publishing)
            pub_thread.start()
            self.publisher_threads.append(pub_thread)
            console_out(f"Publisher {prod_id} started", self.actor)

    def stop_all_publishers(self):
        for publisher in self.publishers:
            publisher.stop_publishing()

        for pub_thread in self.publisher_threads:
            pub_thread.join()

    def get_total_msg_set(self):
        all = set()
        for publisher in self.publishers:
            all = all.union(publisher.get_msg_set())

        return all

    def get_total_pos_ack_count(self):
        total = 0
        for publisher in self.publishers:
            total += publisher.get_pos_ack_count()

        return total

    def get_total_neg_ack_count(self):
        total = 0
        for publisher in self.publishers:
            total += publisher.get_neg_ack_count()

        return total