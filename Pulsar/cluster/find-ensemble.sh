#!/bin/bash

CONTAINER_ID=$(docker ps | grep zk1 | awk '{ print $1 }')
docker exec -it $CONTAINER_ID bin/pulsar zookeeper-shell get /ledgers/00/0000/L0000 | grep ensembleMember