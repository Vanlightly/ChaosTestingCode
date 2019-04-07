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
        self.actor = f"CONSUMER(Test:{test_number} Id:C{consumer_id})"
        self.terminate = False
        self.topic = None
        self.on_assignment_ctr = 0

    def get_partitions(self, partitions):
        ps = list()
        for p in partitions:
            ps.append(str(p.partition))

        if len(ps) == 0:
            return "none"
        else:
            return ",".join(ps)

    def on_assignment(self, con, partitions):
        console_out(f"Assigned partitions: {self.get_partitions(partitions)}", self.actor)

        if self.on_assignment_ctr == 0:
            self.on_assignment_ctr += 1
            for part in partitions:
                part.offset = 0

        self.consumer.assign(partitions)

    def on_revoke(self, con, partitions):
        console_out(f"Unassigned partitions: {self.get_partitions(partitions)}", self.actor)
        self.consumer.unassign()

    def create_consumer(self, group_id, topic):
        self.terminate = False
        console_out(f"Creating a consumer with bootstrap.servers: {self.broker_manager.get_bootstrap_servers()}", self.actor)
        self.consumer = Consumer({
                            'bootstrap.servers': self.broker_manager.get_bootstrap_servers(),
                            'api.version.request': True,
                            'enable.auto.commit': True,
                            'group.id': group_id,
                            'auto.offset.reset': 'earliest',
                            'default.topic.config': {
                                'auto.offset.reset': 'smallest'
                            }
        })
        self.topic = topic

    def subscribe(self):
        subscribed = False
        while not subscribed:
            try:
                console_out(f"Starting subscription to {self.topic}", self.actor)
                self.consumer.subscribe([self.topic], on_assign=self.on_assignment, on_revoke=self.on_revoke)
                console_out(f"Subscribed to {self.topic}", self.actor)
                subscribed = True
            except KafkaError as e:
                console_out(f"Failed to subscribe: {e}", self.actor)
                time.sleep(5)


    def start_consuming(self):
        self.subscribe()

        try:
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

            console_out("Consumption terminated", self.actor)
            self.consumer.close()
        except Exception as e:
            console_out("Consumption terminated due to error", self.actor)
            template = "An exception of type {0} occurred. Arguments:{1!r}"
            message = template.format(type(e).__name__, e.args)
            console_out(message, self.actor)
    
    def stop_consuming(self):
        self.terminate = True
