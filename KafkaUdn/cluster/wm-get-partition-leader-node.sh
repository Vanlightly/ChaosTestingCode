#!/bin/bash

cd ../cluster

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
node_num=$(docker exec -t -w /opt/kafka/bin $CONTAINER_ID ./kafka-topics.sh --zookeeper zk1:2181 --topic $2 --describe | grep "Partition: $3" | awk '{ print $6; }')
echo "kafka$node_num"