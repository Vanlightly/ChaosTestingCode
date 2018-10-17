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
        echo "TODO"
        ;;
    *)
        echo "Chaos action not recognized"
        ;;
esac