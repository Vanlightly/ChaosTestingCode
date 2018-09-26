#!/bin/bash

R_ID=$(blockade status | grep $1 | awk '{ print $2 }')
docker exec -it $R_ID bash -c "rabbitmqctl forget_cluster_node rabbit@$2"