#!/bin/bash

broker=$(bash find-topic-owner.sh "$1" "$2")
echo "killing $broker"
blockade kill "$broker"
echo "$broker killed"
