#!/bin/bash

# $1 E
# $2 Qw
# $3 Qa
# $4 Pulsar broker count
# $5 Bookie count
# $6 deduplication_enabled

cd ../cluster

if blockade status > /dev/null 2>&1; then
    echo Destroying blockade cluster
    blockade destroy
fi

echo Creating blockade cluster
if [[ $6 == "true" ]]; then
    if [[ $4 == 3 && $5 == 2 ]]; then
        cp ./blockade-files/blockade-3p-2b-dedup.yml blockade.yml
    elif [[ $4 == 3 && $5 == 3 ]]; then
        cp ./blockade-files/blockade-3p-3b-dedup.yml blockade.yml
    elif [[ $4 == 3 && $5 == 4 ]]; then
        cp ./blockade-files/blockade-3p-4b-dedup.yml blockade.yml
    elif [[ $4 == 3 && $5 == 5 ]]; then
        cp ./blockade-files/blockade-3p-5b-dedup.yml blockade.yml
    elif [[ $4 == 3 && $5 == 6 ]]; then
        cp ./blockade-files/blockade-3p-6b-dedup.yml blockade.yml
    else
        echo This combination of Pulsar brokers and Bookies is not supported
        exit 1
    fi
else
    if [[ $4 == 3 && $5 == 2 ]]; then
        cp ./blockade-files/blockade-3p-2b.yml blockade.yml
    elif [[ $4 == 3 && $5 == 3 ]]; then
        cp ./blockade-files/blockade-3p-3b.yml blockade.yml
    elif [[ $4 == 3 && $5 == 4 ]]; then
        cp ./blockade-files/blockade-3p-4b.yml blockade.yml
    elif [[ $4 == 3 && $5 == 5 ]]; then
        cp ./blockade-files/blockade-3p-5b.yml blockade.yml
    elif [[ $4 == 3 && $5 == 6 ]]; then
        cp ./blockade-files/blockade-3p-6b.yml blockade.yml
    else
        echo This combination of Pulsar brokers and Bookies is not supported
        exit 1
    fi
fi

if ! blockade up > /dev/null 2>&1; then
    echo Blockade error, aborting test
    exit 1
fi

nodes=$(bash list-nodes.sh)
echo "Running test with config: E $1 Qw $2 Qa $3 with nodes $nodes"

echo Creating tenant and namespace with configuration $1-$2-$3
bash setup-scenario.sh $1 $2 $3