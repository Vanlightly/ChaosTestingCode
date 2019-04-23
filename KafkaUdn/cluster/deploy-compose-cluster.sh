#!/bin/bash

# $1 Kafka broker count
# $2 image version: confluent or wurstmeister

cd ../cluster

if docker-compose ps | grep kafka > /dev/null 2>&1; then
    echo "There is an existing cluster, executing docker-compose down..."
    docker-compose down
fi

echo Creating Docker Compose cluster
if [[ $1 == "3" ]]; then
    if [[ $2 == "confluent" ]]; then
        echo "Copying docker-compose file for 3 node confluent cluster"
        cp ./docker-compose-files/docker-compose-3b-cp.yml docker-compose.yml
    else
        echo "Copying docker-compose file for 3 node wurstmeister cluster"
        cp ./docker-compose-files/docker-compose-3b-wm.yml docker-compose.yml
    fi
else
    echo "Only a 3 broker cluster is supported at this time"
    exit 1
fi

echo "Executing docker-compose up..."
if ! docker-compose up -d > /dev/null 2>&1; then
    echo Docker compose error, aborting test
    exit 1
else
    docker-compose ps
fi

