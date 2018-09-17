#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -t $CONTAINER_ID kafka-topics --create --zookeeper zk1:2181 --replication-factor 3 --partitions 1 --topic $2
sleep 2
bash print-topic-details.sh $1 $2