from confluent_kafka import Consumer, KafkaError
import sys
import uuid
from printer import console_out

class KafkaConsumer:
    def __init__(self, broker_manager, msg_monitor, consumer_id, test_number):
        self.consumer = None
        self.broker_manager = broker_manager
        self.msg_monitor = msg_monitor
        self.consumer_id = consumer_id
        self.actor = f"CONSUMER(Test:{test_number} Id:{consumer_id})"
        self.terminate = False
        self.topic = None

    def on_assignment(self, con, partitions):
        for p in partitions:
            p.offset = 0
        console_out(f"Assigned partitions {partitions}", self.actor)
        self.consumer.assign(partitions)

    def on_revoke(self, con, partitions):
        self.consumer.unassign()
        console_out(f"Unassigned partitions {partitions}", self.actor)

    def create_consumer(self, group_id, topic):
        self.terminate = False
        self.consumer = Consumer({
                            'bootstrap.servers': self.broker_manager.get_bootstrap_servers(),
                            'api.version.request': True,
                            'enable.auto.commit': True,
                            'group.id': group_id,
                            'auto.offset.reset': 'earliest'
                            #'default.topic.config': {
                            #    'auto.offset.reset': 'smallest'
                            #}
        })
        self.topic = topic

    def start_consuming(self):
        self.consumer.subscribe([self.topic], on_assign=self.on_assignment, on_revoke=self.on_revoke)
        msg_ctr = 0
        while not self.terminate:
            msg = self.consumer.poll(2.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    console_out(msg.error(), self.actor)
                    break

            self.msg_monitor.append(msg.value(), self.consumer_id, self.actor)

        self.consumer.close()
    
    def stop_consuming(self):
        self.terminate = True
