#!/bin/bash

set -e

echo "Updating advertised listener in $1 container (broker $2) with IP $3"
CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID /bin/bash <<EOF
sed -i "/advertised.listeners=/c\advertised.listeners=LISTENER_DOCKER_INTERNAL://$1:19092,LISTENER_DOCKER_EXTERNAL://$3:9092" /etc/kafka/kafka.properties

cd usr/bin
./kafka-configs --alter --bootstrap-server $1:19092 --entity-type brokers --entity-name $2 --add-config advertised.listeners=[LISTENER_DOCKER_INTERNAL://$1:19092,LISTENER_DOCKER_EXTERNAL://$3:9092]
EOF

echo "Advertised listener corrected in $1"
