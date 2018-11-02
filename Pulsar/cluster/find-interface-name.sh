#!/bin/bash

for iface in $(ifconfig | cut -d ' ' -f1| tr '\n' ' ' | sed -r 's/://g')
do 
    addr=$(ip -o -4 addr list $iface | awk '{print $4}' | cut -d/ -f1)

    if [[ $addr = $1* ]]; then
        echo $iface
    fi
done