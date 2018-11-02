#!/bin/bash

# $1 action
# $2 action specific argument

cd ../cluster

case "$1" in
    no-fail)
        echo "No chaos action to perform"
        ;;
    kill-broker)
        broker=$(bash find-topic-owner.sh pulsar1 "$2")
        echo "-------------------------------------------------"
        echo "$broker is the topic owner, killing $broker!!!!!!"
        echo "-------------------------------------------------"
        blockade kill "$broker"
        echo "-------------------------------------------------"
        echo "$broker KILLED!"
        echo "-------------------------------------------------"
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
        blockade start "$2"
        echo "-------------------------------------------------"
        echo "$2 STARTED!"
        echo "-------------------------------------------------"
        ;;
    kill-bookie)
        bookie=$(bash find-bookie-in-first-ledger.sh)
        echo "-------------------------------------------------"
        echo "$bookie is in the current ledger ensemble, killing $bookie!!!!!!"
        echo "-------------------------------------------------"
        blockade kill "$bookie"
        echo "-------------------------------------------------"
        echo "$bookie KILLED!";
        echo "-------------------------------------------------"
        ;;
    kill-bookies)
        echo "-------------------------------------------------"
        echo "Identifing first $3 bookies in ensemble"
        echo "-------------------------------------------------"
        blockade kill $(bash find-bookies-in-first-ledger.sh $3)
        echo "-------------------------------------------------"
        echo "$3 BOOKIES KILLED!";
        echo "-------------------------------------------------"
        ;;
    isolate-broker-from-zk)
        echo "$3 is the topic owner, isolating $3 from zookeepr!!!!!!"
        blockade partition $4 $5
        echo "-------------------------------------------------"
        echo "$3 ISOLATED!";
        echo "-------------------------------------------------"
        ;;
    isolate-bookie-from-zk)
        echo "$3 is a bookie in the first ledger, isolating $3 from zookeepr!!!!!!"
        blockade partition $4 $5
        echo "-------------------------------------------------"
        echo "$3 ISOLATED!";
        echo "-------------------------------------------------"
        ;;
    custom-isolation)
        echo "Performing custom isolation $3"
        blockade partition $3
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