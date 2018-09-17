from kafka import KafkaConsumer, TopicPartition
import sys

bs = ['172.17.0.3:9092', '172.17.0.4:9093', '172.17.0.5:9094']

topic = sys.argv[1]
consumer_group = sys.argv[2]

consumer = KafkaConsumer(
        bootstrap_servers=bs,
        group_id=consumer_group,
        enable_auto_commit=False
    )


for p in consumer.partitions_for_topic(topic):
    tp = TopicPartition(topic, p)
    consumer.assign([tp])
    committed = consumer.committed(tp)
    consumer.seek_to_end(tp)
    last_offset = consumer.position(tp)
    print("topic: %s partition: %s committed: %s last: %s lag: %s" % (topic, p, committed, last_offset, (last_offset - committed)))

consumer.close(autocommit=False)

