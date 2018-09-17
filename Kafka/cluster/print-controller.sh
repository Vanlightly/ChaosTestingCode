#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -t $CONTAINER_ID zookeeper-shell zk1:2181 get /controller | grep brokerid | jq -r '.brokerid'