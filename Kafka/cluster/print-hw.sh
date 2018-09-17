#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -t $CONTAINER_ID kafka-run-class kafka.tools.GetOffsetShell --broker-list $1:$2 --time -1 --topic $3