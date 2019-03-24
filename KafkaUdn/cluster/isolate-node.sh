#!/bin/bash

cd ../cluster

echo "CHAOS: Partitioning $1"
blockade partition $1
echo "CHAOS: $1 partitioned"