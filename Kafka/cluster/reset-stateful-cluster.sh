#!/bin/bash

set -e

# this version deletes the volume data of the three kafka brokers

blockade destroy
find ./volumes ! -name '.*' ! -type d -exec rm -f -- {} +
blockade up
sleep 5
bash update-hosts.sh