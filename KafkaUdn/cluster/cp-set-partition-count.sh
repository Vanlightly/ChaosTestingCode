#!/bin/bash

cd ../cluster
CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID kafka-topics --alter --zookeeper zk1:2181 --topic $2 --partitions $3

bash cp-print-topic-details.sh $1 $2