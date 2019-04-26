#!/bin/bash

FILE_NAME=$2/$1.log
mkdir -p $2
docker logs $1 > $FILE_NAME
gzip $FILE_NAME
echo "GZipped logs of $1 to $FILE_NAME"

CRASH_DUMP=$2/$1_erl_crash.dump
if ! docker cp $1:/var/lib/rabbitmq/erl_crash.dump $CRASH_DUMP > /dev/null 2>&1; then
    echo "No crash dump to copy"
else
    echo "Copied crash dump to $CRASH_DUMP"
fi
