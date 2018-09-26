#!/bin/bash

set -e

if [ $1 = "rabbitmq1" ]; then
    blockade restart rabbitmq1
    echo "rabbitmq1 restarted"
elif [ $1 = "rabbitmq2" ]; then
    # node 2 does not have rabbitmq-server as pid 1 and so stopping the container causes an unclean shutdown
    # therefore we do a controlled stop first
    R2_ID=$(blockade status | grep rabbitmq2 | awk '{ print $2 }')    
    docker exec -it $R2_ID rabbitmqctl stop_app
    
    # restart the container
    blockade restart rabbitmq2
    echo "rabbitmq2 restarted"

elif [ $1 = "rabbitmq3" ]; then
    # node 3 does not have rabbitmq-server as pid 1 and so stopping the container causes an unclean shutdown
    # therefore we do a controlled stop first
    R3_ID=$(blockade status | grep rabbitmq3 | awk '{ print $2 }')    
    docker exec -it $R3_ID rabbitmqctl stop_app
        
    # restart the container
    blockade restart rabbitmq3
    echo "rabbitmq3 restarted"
fi
