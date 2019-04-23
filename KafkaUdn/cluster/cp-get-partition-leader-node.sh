#!/bin/bash

cd ../cluster

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
node_num=$(docker exec -i $CONTAINER_ID kafka-topics --zookeeper zk1:2181 --topic $2 --describe | grep "Partition: $3" | awk '{ print $6; }')
echo "kafka$node_num"