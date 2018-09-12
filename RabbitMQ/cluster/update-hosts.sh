#!/bin/bash

echo "Acquiring container ids and ip addresses"
R1_ID=$(blockade status | grep rabbitmq1 | awk '{ print $2 }')
R2_ID=$(blockade status | grep rabbitmq2 | awk '{ print $2 }')
R3_ID=$(blockade status | grep rabbitmq3 | awk '{ print $2 }')

R1_IP_ADDR=$(blockade status | grep rabbitmq1 | awk '{ print $4 }')
R2_IP_ADDR=$(blockade status | grep rabbitmq2 | awk '{ print $4 }')
R3_IP_ADDR=$(blockade status | grep rabbitmq3 | awk '{ print $4 }')

echo "Updating hosts of rabbitmq1"
# update rabbitmq1
docker exec -it $R1_ID bash -c "cp /etc/hosts ~/hosts.new && echo $R2_IP_ADDR rabbitmq2 blockaderabbit_rabbitmq2 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
docker exec -it $R1_ID bash -c "cp /etc/hosts ~/hosts.new && echo $R3_IP_ADDR rabbitmq3 blockaderabbit_rabbitmq3 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"

echo "Updating hosts of rabbitmq2"
# update rabbitmq2
docker exec -it $R2_ID bash -c "cp /etc/hosts ~/hosts.new && echo $R3_IP_ADDR rabbitmq3 blockaderabbit_rabbitmq3 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"

echo "Updating hosts of rabbitmq3"
# update rabbitmq3
docker exec -it $R3_ID bash -c "cp /etc/hosts ~/hosts.new && echo $R2_IP_ADDR rabbitmq2 blockaderabbit_rabbitmq2 >> ~/hosts.new && cp -f ~/hosts.new /etc/hosts"
