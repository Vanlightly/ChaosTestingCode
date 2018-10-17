#!/bin/bash

CONTAINER_ID=$(docker ps | grep zk1 | awk '{ print $1 }')

while true
do
    docker exec -it $CONTAINER_ID bin/pulsar zookeeper-shell ls /ledgers/underreplication/ledgers | grep "^\["
    sleep 1
done