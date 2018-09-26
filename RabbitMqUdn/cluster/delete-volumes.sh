#!/bin/bash

if [ $1 = "all" ]; then
    rm -rf volumes/01/data/*
    rm -rf volumes/02/data/*
    rm -rf volumes/03/data/*
elif [ $1 = "rabbitmq1" ]; then
    rm -rf volumes/01/data/*
elif [ $1 = "rabbitmq2" ]; then
    rm -rf volumes/02/data/*
elif [ $1 = "rabbitmq3" ]; then
    rm -rf volumes/03/data/*
fi