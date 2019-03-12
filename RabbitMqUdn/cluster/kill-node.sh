#!/bin/bash

set -e

cd ../cluster

if [ $1 = "rabbitmq1" ]; then
    echo "CHAOS: killing rabbitmq1"
    blockade kill rabbitmq1
    echo "CHAOS: rabbitmq1 killed"
elif [ $1 = "rabbitmq2" ]; then
    echo "CHAOS: killing rabbitmq2"
    blockade kill rabbitmq2
    echo "CHAOS: rabbitmq2 killed"

elif [ $1 = "rabbitmq3" ]; then
    echo "CHAOS: killing rabbitmq3"
    blockade kill rabbitmq3
    echo "CHAOS: rabbitmq3 killed"
fi
