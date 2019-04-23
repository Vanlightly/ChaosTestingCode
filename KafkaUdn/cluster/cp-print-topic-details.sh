#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID kafka-topics --zookeeper zk1:2181 --topic $2 --describe