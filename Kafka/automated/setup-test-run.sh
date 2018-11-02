#!/bin/bash

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

bash update-hosts.sh