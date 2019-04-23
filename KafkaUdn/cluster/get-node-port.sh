#!/bin/bash

echo $(docker port $1 | grep 0:909 | cut -c-4)
