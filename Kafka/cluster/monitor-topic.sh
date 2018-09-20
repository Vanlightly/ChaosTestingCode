#!/bin/bash

while true
do

    CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
    docker exec -t $CONTAINER_ID kafka-topics --zookeeper zk1:2181 --topic $3 --describe
    #docker exec -t $CONTAINER_ID kafka-run-class kafka.tools.GetOffsetShell --broker-list $1:$2 --time -1 --topic $3

done