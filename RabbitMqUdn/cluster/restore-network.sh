#!/bin/bash

cd ../cluster

if [ $1 = "all" ]; then
    echo "CHAOS: restoring network speed and reliability for all nodes"
    blockade fast --all
    echo "CHAOS: network speed and reliability restored for all nodes"
else
    echo "CHAOS: restoring network speed and reliability for $1"
    blockade fast $1
    echo "CHAOS: network speed and reliability restored for $1"
fi