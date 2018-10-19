#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
owner_line=$(docker exec -it $CONTAINER_ID bin/pulsar-admin topics stats-internal persistent://vanlightly/cluster-1/ns1/$2 | grep lastConfirmedEntry)
echo $(echo $owner_line | awk '{ print $3; }')