#!/bin/bash

# $1 Kafka broker count

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo Destroying blockade cluster
    blockade destroy
fi

echo Creating blockade cluster
if [[ $1 == "3" ]]; then
    echo "Creating 3 node cluster"
    cp ./blockade-files/blockade-kafka-3b.yml blockade.yml
else
    echo "Only a 3 broker cluster is supported at this time"
    exit 1
fi

if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
fi