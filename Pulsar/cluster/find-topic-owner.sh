#!/bin/bash

# $1 pulsar broker to run the pulsar-admin tool on
# $2 topic name

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
owner_line=$(docker exec -it $CONTAINER_ID bin/pulsar-admin topics lookup persistent://vanlightly/cluster-1/ns1/$2)

# format is always the same: "pulsar://pulsar1:6650"
echo $(echo "$owner_line" | cut -c 11-17)