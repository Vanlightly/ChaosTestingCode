#!/bin/bash

sudo tcpkill -i docker0 host $1 &
sleep 7
for child in $(jobs -p); do
    echo kill "$child" && kill "$child"
done
wait $(jobs -p)