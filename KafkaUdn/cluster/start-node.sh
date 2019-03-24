#!/bin/bash

set -e

cd ../cluster

echo "CHAOS: starting $1"
blockade start $1
echo "CHAOS: $1 started"
