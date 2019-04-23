#!/bin/bash

cd ../cluster
CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i -w /opt/kafka/bin $CONTAINER_ID /bin/bash ./kafka-topics.sh --alter --zookeeper zk1:2181 --topic $2 --partitions $3

bash wm-print-topic-details.sh $1 $2