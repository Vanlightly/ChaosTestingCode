#!/bin/bash

blockade status | { while read line; \
do \
    if [[ $line == bookie* ]] || [[ $line == pulsar* ]] || [[ $line == proxy* ]] || [[ $line == zk* ]]; then \
        node=$(echo $(echo $line | awk '{ print $1; }')); \
        nodes+="$node "; \
    fi; \
done; \

echo "$nodes"; }
