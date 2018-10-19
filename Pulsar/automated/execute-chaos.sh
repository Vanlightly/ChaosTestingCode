#!/bin/bash

# $1 action
# $2 topic
# $3 verbose logging

cd ../cluster

case "$1" in
    no-fail)
        echo "No chaos action to perform"
        ;;
    kill-broker)
        broker=$(bash find-topic-owner.sh pulsar1 "$2")
        echo "$broker is the topic owner, killing $broker!!!!!!"
        blockade kill "$broker"
        echo "$broker killed!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
        ;;
    kill-bookie)
        bookie=$(bash find-bookie-to-kill.sh)
        echo "$bookie is in the current ledger ensemble, killing $bookie!!!!!!"
        blockade kill "$bookie"
        echo "$bookie killed!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
        ;;
    isolate-broker-from-zk)
        echo "$3 is the topic owner, isolating $3 from zookeepr!!!!!!"
        blockade partition $4 $5
        echo "$3 isolated!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
        ;;
    isolate-bookie-from-zk)
        echo "$3 is a bookie in the first ledger, isolating $3 from zookeepr!!!!!!"
        blockade partition $4 $5
        echo "$3 isolated!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
        ;;
    custom-isolation)
        echo "Performing custom isolation $3"
        blockade partition $3
        echo "isolated!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
        ;;
    *)
        echo "Chaos action not recognized"
        ;;
esac