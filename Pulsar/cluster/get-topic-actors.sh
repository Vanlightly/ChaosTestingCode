#!/bin/bash

# $1 pulsar broker to run the pulsar-admin tool on
# $2 topic name

echo Topic owner broker: 
CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -it $CONTAINER_ID bin/pulsar-admin topics lookup persistent://vanlightly/cluster-1/ns1/$2

echo Bookie ensemble
bash find-ensemble.sh