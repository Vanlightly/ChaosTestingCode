#!/bin/bash

set -e

if [ ! -f is-member-of-cluster.txt ]; then

    touch is-member-of-cluster.txt

    # Start RMQ from entry point.
    # This will ensure that environment variables passed
    # will be honored
    /usr/local/bin/docker-entrypoint.sh rabbitmq-server -detached

    # Do the cluster dance
    rabbitmqctl stop_app
    # Wait a while for the app to really stop
    sleep 2s
    
    rabbitmqctl join_cluster rabbit@rabbitmq1

    # Stop the entire RMQ server. This is done so that we
    # can attach to it again, but without the -detached flag
    # making it run in the forground
    rabbitmqctl stop

    # Wait a while for the app to really stop
    sleep 2s

    # Start it
    rabbitmq-server
else
    rabbitmq-server

fi
# wipe all data when server stops
#rm -rf /var/lib/rabbitmq/mnesia