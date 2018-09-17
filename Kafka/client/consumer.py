from confluent_kafka import Consumer, KafkaError
import sys

topic = sys.argv[1]

c = Consumer({
    'bootstrap.servers': '172.17.0.3:9092,172.17.0.4:9093,172.17.0.5:9094',
    'group.id': 'mygroup',
    'default.topic.config': {
        'auto.offset.reset': 'smallest'
    }
})

c.subscribe([topic])

while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            continue
        else:
            print(msg.error())
            break

    print('Received message: {}'.format(msg.value().decode('utf-8')))

c.close()