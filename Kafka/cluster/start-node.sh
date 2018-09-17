#!/bin/bash

blockade start $1

echo "Acquiring container ids and ip addresses"
K1_ID=$(docker ps | grep kafka1 | awk '{ print $1 }')
K2_ID=$(docker ps | grep kafka2 | awk '{ print $1 }')
K3_ID=$(docker ps | grep kafka3 | awk '{ print $1 }')
ZK1_ID=$(docker ps | grep zk1 | awk '{ print $1 }')

K1_IP_ADDR=$(blockade status | grep kafka1 | awk '{ print $4 }')
K2_IP_ADDR=$(blockade status | grep kafka2 | awk '{ print $4 }')
K3_IP_ADDR=$(blockade status | grep kafka3 | awk '{ print $4 }')
ZK1_IP_ADDR=$(blockade status | grep zk1 | awk '{ print $4 }')

if [ $1 = "kafka1" ]; then
    echo "Updating hosts of kafka1"
    docker exec -it $K1_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K2_IP_ADDR kafka2 cluster_kafka2 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
    docker exec -it $K1_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K3_IP_ADDR kafka3 cluster_kafka3 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
elif [ $1 = "kafka2" ]; then
    echo "Updating hosts of kafka2"
    docker exec -it $K2_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K1_IP_ADDR kafka1 cluster_kafka1 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
    docker exec -it $K2_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K3_IP_ADDR kafka3 cluster_kafka3 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
elif [ $1 = "kafka3" ]; then
    echo "Updating hosts of kafka3"
    docker exec -it $K3_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K1_IP_ADDR kafka1 cluster_kafka1 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
    docker exec -it $K3_ID bash -c "cp /etc/hosts ~/hosts.new && echo $K2_IP_ADDR kafka2 cluster_kafka2 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
fi