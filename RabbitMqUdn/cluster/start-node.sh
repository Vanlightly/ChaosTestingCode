#!/bin/bash

set -e

cd ../cluster

if [ $1 = "rabbitmq1" ]; then
    blockade start rabbitmq1
    echo "CHAOS: rabbitmq1 restarted"
elif [ $1 = "rabbitmq2" ]; then
    # start the container
    blockade start rabbitmq2
    echo "CHAOS: rabbitmq2 restarted"

elif [ $1 = "rabbitmq3" ]; then
    # start the container
    blockade start rabbitmq3
    echo "CHAOS: rabbitmq3 restarted"
fi
