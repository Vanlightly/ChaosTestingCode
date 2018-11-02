#!/bin/bash
cd ../cluster

blockade status | { while read line; \
do \
    if [[ $line == kafka* ]]; then \
        state=$(echo $(echo $line | awk '{ print $3; }')); \
        if [[ $state == "UP" ]]; then \
            node=$(echo $(echo $line | awk '{ print $1; }')); \
            node_ip=$(echo $(echo $line | awk '{ print $4; }')); \
            if [[ $node == "kafka1" ]]; then \
                nodes+="$node_ip:9092 "; \
            elif [[ $node == "kafka2" ]]; then \
                nodes+="$node_ip:9093 "; \
            elif [[ $node == "kafka3" ]]; then \
                nodes+="$node_ip:9094 "; \
            fi; \
        fi; \
    fi; \
done; \

echo "$nodes"; }
