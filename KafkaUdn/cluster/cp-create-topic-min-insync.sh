#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID kafka-topics --create --zookeeper zk1:2181 --replication-factor $3 --partitions $4 --topic $2 --config min.insync.replicas=$5
sleep 2
bash cp-print-topic-details.sh $1 $2