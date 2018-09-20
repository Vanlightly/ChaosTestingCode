#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -t $CONTAINER_ID kafka-topics --alter --zookeeper zk1:2181 --topic $2 --config unclean.leader.election.enable=true
sleep 2
bash print-topic-details.sh $1 $2