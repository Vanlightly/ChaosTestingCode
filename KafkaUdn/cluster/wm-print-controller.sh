#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
CONTROLLER=$(docker exec -w /opt/kafka/bin $CONTAINER_ID /bin/bash ./zookeeper-shell.sh zk1:2181 get /controller | grep brokerid | jq -r '.brokerid')

echo "CONTROLLER IS KAFKA$CONTROLLER"
