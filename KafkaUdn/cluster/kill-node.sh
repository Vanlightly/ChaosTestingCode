#!/bin/bash

set -e

cd ../cluster

echo "CHAOS: killing $1"
blockade kill $1
echo "CHAOS: $1 killed"
