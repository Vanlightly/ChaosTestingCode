#!/bin/bash

# $1 Kafka broker count
# $2 image version: confluent or wurstmeister

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo "There is an existing cluster, executing blockade destroy..."
    blockade destroy
fi

echo Creating blockade cluster
if [[ $1 == "3" ]]; then
    if [[ $2 == "confluent" ]]; then
        echo "Copying blockade file for a 3 node confluent cluster"
        cp ./blockade-files/blockade-kafka-3b-cp-manager.yml blockade.yml
    else
        echo "Copying blockade file for a 3 node wurstmeister cluster"
        cp ./blockade-files/blockade-kafka-3b-wm-manager.yml blockade.yml
    fi
else
    echo "Only a 3 broker cluster is supported at this time"
    exit 1
fi

echo "Executing blockade up..."
if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
else
    blockade status
fi