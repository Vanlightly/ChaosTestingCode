# ChaosTestingCode
Code for doing chaos testing on various distributed messaging systems.

## Folders guide

### Kafka
Code for blog posts:
- https://jack-vanlightly.com/blog/2018/9/14/how-to-lose-messages-on-a-kafka-cluster-part1
- https://jack-vanlightly.com/blog/2018/9/18/how-to-lose-messages-on-a-kafka-cluster-part-2
- https://jack-vanlightly.com/blog/2018/10/25/testing-producer-deduplication-in-apache-kafka-and-apache-pulsar

Now legacy code. More advanced code is being worked on in the KafkaUdn folder.

### KafkaUdn
Uses the UDN feature of Blockade to make deploying clusters more simple than in the Kafka folder. It also has more advanced automated tests than the Kafka folder.

See the dedicated readme for more: https://github.com/Vanlightly/ChaosTestingCode/blob/master/KafkaUdn/readme.md

### RabbitMQ
Code for blog post:
- https://jack-vanlightly.com/blog/2018/9/10/how-to-lose-messages-on-a-rabbitmq-cluster

Now legacy code. More advanced code is being worked on in the RabbitMqUdn folder.

### RabbitMqUdn
A more advanced, fully automated version of the RabbitMQ folder, using the UDN feature of Blockade to simplify deploying a cluster.

The code is primarily focused on testing RabbitMQ 3.8 features of quorum queues and single active consumer. But also has support for mirrored queues.

See the dedicated readme for more info: https://github.com/Vanlightly/ChaosTestingCode/blob/master/RabbitMqUdn/readme.md

### Pulsar
Code for blog post:
- https://jack-vanlightly.com/blog/2018/10/21/how-to-not-lose-messages-on-an-apache-pulsar-cluster
- https://jack-vanlightly.com/blog/2018/10/25/testing-producer-deduplication-in-apache-kafka-and-apache-pulsar

Uses the UDN feature of Blockade.
