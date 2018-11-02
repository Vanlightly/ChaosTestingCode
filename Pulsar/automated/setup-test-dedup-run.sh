#!/bin/bash

# $1 E
# $2 Qw
# $3 Qa
# $4 deduplication_enabled
# $5 slow

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo Destroying blockade cluster
    blockade destroy
fi

echo Creating blockade cluster
if [[ $4 == "true" ]]; then
    if [[ $5 == "true" ]]; then
        cp ./blockade-files/blockade-3p-3b-dedup-slow.yml blockade.yml
    else
        cp ./blockade-files/blockade-3p-3b-dedup.yml blockade.yml
    fi
else
    if [[ $5 == "true" ]]; then
        cp ./blockade-files/blockade-3p-3b-slow.yml blockade.yml
    else
        cp ./blockade-files/blockade-3p-3b.yml blockade.yml
    fi
fi

if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
fi

if [[ $5 == "true" ]]; then
    blockade slow proxy pulsar1 pulsar2 pulsar3
fi

nodes=$(bash list-nodes.sh)
echo "Running test with config: E $1 Qw $2 Qa $3 with nodes $nodes"

echo Creating tenant and namespace with configuration $1-$2-$3
bash setup-scenario.sh $1 $2 $3