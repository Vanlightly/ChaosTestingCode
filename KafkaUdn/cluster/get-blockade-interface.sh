#!/bin/bash

cd ../cluster 

echo $(ifconfig | head -n 1 | awk -F: '{print $1}')