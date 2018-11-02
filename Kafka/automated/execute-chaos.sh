#!/bin/bash

# $1 action
# $2 action specific argument

cd ../cluster

case "$1" in
    no-fail)
        echo "No chaos action to perform"
        ;;
    kill-specific-node)
        echo "-------------------------------------------------"
        echo "Killing $2!"
        echo "-------------------------------------------------"
        blockade kill "$2"
        echo "-------------------------------------------------"
        echo "$2 KILLED!"
        echo "-------------------------------------------------"
        ;;
    start-specific-node)
        echo "-------------------------------------------------"
        echo "Starting $2!"
        echo "-------------------------------------------------"
        bash start-node.sh "$2"
        echo "-------------------------------------------------"
        echo "$2 STARTED!"
        echo "-------------------------------------------------"
        ;;
    isolate-broker-from-zk)
        echo "$2 has partition leader, isolating $3 from zookeepr!!!!!!"
        blockade partition $3 $4
        echo "-------------------------------------------------"
        echo "$2 ISOLATED!";
        echo "-------------------------------------------------"
        ;;
    custom-isolation)
        echo "Performing custom isolation $2"
        blockade partition $2
        echo "-------------------------------------------------"
        echo "ISOLATED!"
        echo "-------------------------------------------------"
        ;;
    resolve-partitions)
        echo "Resolving partitions"
        blockade join
        echo "-------------------------------------------------"
        echo "PARTITION RESOLVED!"
        echo "-------------------------------------------------"
        ;;
    *)
        echo "Chaos action not recognized"
        ;;
esac