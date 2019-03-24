#!/bin/bash

cd ../cluster

if [ $1 = "all" ]; then
    echo "CHAOS: Starting flaky network for all"
    blockade flaky --all
    echo "CHAOS: Flaky network started for all"
else
    echo "CHAOS: Starting flaky network for $1"
    blockade flaky $1
    echo "CHAOS: Flaky network started for $1"
fi