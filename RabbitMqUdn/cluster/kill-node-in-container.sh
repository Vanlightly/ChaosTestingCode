#!/bin/bash

CONTAINER_ID=$(blockade status | grep $1 | awk '{ print $2 }')
docker exec -it $CONTAINER_ID bash -c 'echo Killing $(ps aux | grep rabbitmq-server | grep -v grep | awk '"'"'{ print $2 }'"'"')'
docker exec -it $CONTAINER_ID bash -c 'kill -9 $(ps aux | grep rabbitmq-server | grep -v grep | awk '"'"'{ print $2 }'"'"')'