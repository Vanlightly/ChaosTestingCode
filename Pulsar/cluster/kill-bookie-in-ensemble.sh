#!/bin/bash

bk=$(bash find-bookie-to-kill.sh "$1" "$2")
echo killing "$bk"
blockade kill "$bk"
echo "$bk" killed