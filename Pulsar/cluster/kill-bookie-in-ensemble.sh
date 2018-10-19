#!/bin/bash

bk=$(bash find-bookie-to-kill.sh)
echo killing "$bk"
blockade kill "$bk"
echo "$bk" killed