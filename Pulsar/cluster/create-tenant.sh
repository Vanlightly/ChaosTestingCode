#!/bin/bash

# $1 pulsar broker to run the pulsar-admin tool on
# $2 tenant

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -it $CONTAINER_ID bin/pulsar-admin tenants create $2