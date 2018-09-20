#!/bin/bash

set -e

if [ $1 = "rabbitmq1" ]; then
    R2_ID=$(blockade status | grep rabbitmq2 | awk '{ print $2 }')
    docker exec -it $R2_ID rabbitmqctl stop_app

    R3_ID=$(blockade status | grep rabbitmq3 | awk '{ print $2 }')
    docker exec -it $R3_ID rabbitmqctl stop_app

    echo "cluster stopped"

    docker exec -it $R2_ID rabbitmqctl forget_cluster_node rabbit@rabbitmq1

    echo "rabbitmq1 forgotten"

    docker exec -it $R2_ID rabbitmqctl start_app
    docker exec -it $R3_ID rabbitmqctl start_app
    echo "cluster started"

elif [ $1 = "rabbitmq2" ]; then
    R1_ID=$(blockade status | grep rabbitmq1 | awk '{ print $2 }')
    docker exec -it $R1_ID rabbitmqctl stop_app

    R3_ID=$(blockade status | grep rabbitmq3 | awk '{ print $2 }')
    docker exec -it $R3_ID rabbitmqctl stop_app

    echo "cluster stopped"

    docker exec -it $R1_ID rabbitmqctl forget_cluster_node rabbit@rabbitmq2

    echo "rabbitmq2 forgotten"

    docker exec -it $R1_ID rabbitmqctl start_app
    docker exec -it $R3_ID rabbitmqctl start_app
    echo "cluster started"

elif [ $1 = "rabbitmq3" ]; then
    R1_ID=$(blockade status | grep rabbitmq1 | awk '{ print $2 }')
    R2_ID=$(blockade status | grep rabbitmq2 | awk '{ print $2 }')
    docker exec -it $R2_ID rabbitmqctl stop_app
    echo "rabbitmq2 stopped"
    
    docker exec -it $R1_ID rabbitmqctl -n rabbit@rabbitmq1 forget_cluster_node rabbit@rabbitmq3
    echo "rabbitmq3 forgotten"

    docker exec -it $R2_ID rabbitmqctl start_app
    echo "rabbitmq2 started"
fi
