#!/bin/bash

# $1 pulsar broker to run the pulsar-admin tool on
# $2 tenant
# $3 namespace
# $4 ensemble size
# $5 write quorum size
# $6 ack quorum size

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -it $CONTAINER_ID bin/pulsar-admin namespaces create $2/cluster-1/$3 && \
docker exec -it $CONTAINER_ID bin/pulsar-admin namespaces set-persistence -e $4 -w $5 -a $6 -r 0 $2/cluster-1/$3
docker exec -it $CONTAINER_ID bin/pulsar-admin namespaces set-retention -s 100M -t 24h $2/cluster-1/$3
