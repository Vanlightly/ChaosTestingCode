#!/bin/bash

# $1 E
# $2 Qw
# $3 Qa

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo Destroying blockade cluster
    blockade destroy
fi

echo Creating blockade cluster
if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
fi

nodes=$(bash list-nodes.sh)
echo "Running test with config: E $1 Qw $2 Qa $3 with nodes $nodes"

echo Creating tenant and namespace with configuration $1-$2-$3
bash setup-scenario.sh $1 $2 $3