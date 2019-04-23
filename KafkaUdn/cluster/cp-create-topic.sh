#!/bin/bash

set -e

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
echo "Using CP $CONTAINER_ID, creating topic $2 with rep factor $3 with $4 partitions. Min-insync-replicas of $5 with unclean failover of $6."
docker exec -i $CONTAINER_ID kafka-topics --create --zookeeper zk1:2181 --topic $2 --replication-factor $3 --partitions $4  --config min.insync.replicas=$5 --config unclean.leader.election.enable=$6
sleep 2

cd ../cluster

bash cp-print-topic-details.sh $1 $2