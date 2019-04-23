#!/bin/bash

# for the wurstmeister image

set -e

echo "Updating advertised listener in $1 container (broker $2) with IP $3"
CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID /bin/bash <<EOF
sed -i "/advertised.listeners=/c\advertised.listeners=PLAINTEXT://$3:9092,PLAINTEXT_IB://$1:29092" /opt/kafka/config/server.properties

cd /opt/kafka/bin
./kafka-configs.sh --alter --bootstrap-server $1:29092 --entity-type brokers --entity-name $2 --add-config advertised.listeners=[PLAINTEXT://$3:9092,PLAINTEXT_IB://$1:29092]
EOF

echo "Advertised listener corrected in $1"
