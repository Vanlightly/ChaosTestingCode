#!/bin/bash

set -e

blockade destroy
blockade up
sleep 5
bash update-hosts.sh