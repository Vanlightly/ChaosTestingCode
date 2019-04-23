#!/bin/bash

cat >> docker-compose.yml <<EOL

  kafka$1:
    image: jackvanlightly/kafka-cp-with-http-reporter:5.2.1-0.3.2
    depends_on:
      - zk1
    ports:
      - $3:9092
      - $4:19092
    environment:
      KAFKA_BROKER_ID: $1
      KAFKA_ZOOKEEPER_CONNECT: zk1:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://$2:9092,PLAINTEXT_IB://kafka$1:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_IB:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT_IB
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_CONFLUENT_SUPPORT_METRICS_ENABLE: "false"
      KAFKA_METRIC_REPORTERS: "cloudkarafka.kafka_http_reporter"
      KAFKA_LEADER_IMBALANCE_CHECK_INTERVAL_SECONDS: 30
EOL

docker-compose up -d