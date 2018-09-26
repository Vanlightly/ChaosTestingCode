#!/bin/bash

set -e

if [ $1 = "rabbitmq1" ]; then
    blockade start rabbitmq1
    echo "rabbitmq1 restarted"
elif [ $1 = "rabbitmq2" ]; then
    # start the container
    blockade start rabbitmq2
    echo "rabbitmq2 restarted"

elif [ $1 = "rabbitmq3" ]; then
    # start the container
    blockade start rabbitmq3
    echo "rabbitmq3 restarted"
fi
