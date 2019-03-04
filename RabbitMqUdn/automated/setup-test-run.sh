#!/bin/bash

# $1 RabbitMQ broker count
# $2 RabbitMQ version (3.7, 3.8)

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo Destroying blockade cluster
    blockade destroy
fi

echo Creating blockade cluster
if [[ $1 == "3" ]]; then
    if [[ $2 == "3.7" ]]; then
        cp ./blockade-files/blockade-rmq-3b-3.7.yml blockade.yml
    elif [[ $2 == "3.8" ]]; then
        cp ./blockade-files/blockade-rmq-3b-3.8.yml blockade.yml
    else
        echo "Only versions 3.7 and 3.8 are supported at this time"
        exit 1
    fi
else
    echo "Only a three broker cluster is supported at this time"
    exit 1
fi

if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
fi