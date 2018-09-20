#!/bin/bash

CONTAINER_ID=$(blockade status | grep $1 | awk '{ print $2 }')
docker exec -it $CONTAINER_ID bash -c 'rm -f is-member-of-cluster.txt'
blockade kill $1