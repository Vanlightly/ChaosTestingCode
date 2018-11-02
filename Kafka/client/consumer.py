from confluent_kafka import Consumer, KafkaError
import sys
import uuid

topic = sys.argv[1]

c = Consumer({
    #'bootstrap.servers': '172.17.0.3:9092,172.17.0.4:9093,172.17.0.5:9094',
    'bootstrap.servers': '172.17.0.4:9093,172.17.0.5:9094',
    'api.version.request': True,
    'enable.auto.commit': True,
    'group.id': str(uuid.uuid1()),
    'auto.offset.reset': 'earliest'
    #'default.topic.config': {
    #    'auto.offset.reset': 'smallest'
    #}
})

def print_assignment(consumer, partitions):
    for p in partitions:
        p.offset = 0
    print('assign', partitions)
    consumer.assign(partitions)

    # Subscribe to topics
c.subscribe([topic], on_assign=print_assignment)

while True:
    msg = c.poll(2.0)

    if msg is None:
        print("No messages")
        continue
    if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            continue
        else:
            print(msg.error())
            break

    print('Received message: {}'.format(msg.value().decode('utf-8')))

c.close()