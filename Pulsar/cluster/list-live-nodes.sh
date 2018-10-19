#!/bin/bash
cd ../cluster

blockade status | { while read line; \
do \
    if [[ $line == bookie* ]] || [[ $line == pulsar* ]] || [[ $line == proxy* ]] || [[ $line == zk* ]]; then \
        state=$(echo $(echo $line | awk '{ print $3; }')); \
        if [[ $state == "UP" ]]; then \
            node=$(echo $(echo $line | awk '{ print $1; }')); \
            nodes+="$node "; \
        fi; \
    fi; \
done; \

echo "$nodes"; }
