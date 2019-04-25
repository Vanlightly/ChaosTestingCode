#!/bin/bash

echo $1 log file: $(docker inspect --format='{{.LogPath}}' $1)