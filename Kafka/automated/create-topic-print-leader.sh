#!/bin/bash

cd ../cluster

echo $(bash create-topic.sh kafka1 $1 | grep Leader | awk '{ print $6; }')