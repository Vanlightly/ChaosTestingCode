#!/bin/bash

cd ../cluster

if $(docker ps | grep -q bookie1); then
    bookie1=$(echo $(bash get-node-ip.sh bookie1))
fi 

if $(docker ps | grep -q bookie2); then
    bookie2=$(echo $(bash get-node-ip.sh bookie2))
fi 

if $(docker ps | grep -q bookie3); then
    bookie3=$(echo $(bash get-node-ip.sh bookie3))
fi 

if $(docker ps | grep -q bookie4); then
    bookie4=$(echo $(bash get-node-ip.sh bookie4))
fi 

if $(docker ps | grep -q bookie5); then
    bookie5=$(echo $(bash get-node-ip.sh bookie5))
fi 

if $(docker ps | grep -q bookie6); then
    bookie6=$(echo $(bash get-node-ip.sh bookie6))
fi

counter=0

bash find-ensemble.sh | while read line;
    do
        if [ -n "$bookie1" ] && $(echo "$line" | grep -q "$bookie1"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie1;
                let "counter=counter+1"
            fi
        fi

        if [ -n "$bookie2" ] && $(echo "$line" | grep -q "$bookie2"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie2;
                let "counter=counter+1"
            fi
        fi

        if [ -n "$bookie3" ] && $(echo "$line" | grep -q "$bookie3"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie3;
                let "counter=counter+1"
            fi
        fi

        if [ -n "$bookie4" ] && $(echo "$line" | grep -q "$bookie4"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie4;
                let "counter=counter+1"
            fi
        fi

        if [ -n "$bookie5" ] && $(echo "$line" | grep -q "$bookie5"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie5;
                let "counter=counter+1"
            fi
        fi

        if [ -n "$bookie6" ] && $(echo "$line" | grep -q "$bookie6"); then
            if [[ "$counter" -lt "$1" ]]; then
                echo bookie6;
                let "counter=counter+1"
            fi
        fi
    done
