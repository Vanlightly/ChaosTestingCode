#!/bin/bash

# sometimes blockade can get into a messed up state
# so we just stop all running containers

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker network prune
