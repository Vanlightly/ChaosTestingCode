#!/bin/bash

cd ../cluster

if [ $1 = "all" ]; then
    echo "CHAOS: Starting slow network for all"
    blockade slow --all
    echo "CHAOS: Slow network started for all"
else
    echo "CHAOS: Starting slow network for $1"
    blockade slow $1
    echo "CHAOS: Slow network started for $1"
fi