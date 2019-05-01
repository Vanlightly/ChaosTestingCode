#!/bin/bash

set -e

docker exec -i -w /go/bin toxiproxy /bin/sh <<EOF

./toxiproxy-cli create P1R1 --listen 0.0.0.0:10000 --upstream rabbitmq1:5672
./toxiproxy-cli create P1R2 --listen 0.0.0.0:20000 --upstream rabbitmq2:5672
./toxiproxy-cli create P1R3 --listen 0.0.0.0:30000 --upstream rabbitmq3:5672

./toxiproxy-cli create C1R1 --listen 0.0.0.0:10001 --upstream rabbitmq1:5672
./toxiproxy-cli create C1R2 --listen 0.0.0.0:20001 --upstream rabbitmq2:5672
./toxiproxy-cli create C1R3 --listen 0.0.0.0:30001 --upstream rabbitmq3:5672

./toxiproxy-cli create C2R1 --listen 0.0.0.0:10002 --upstream rabbitmq1:5672
./toxiproxy-cli create C2R2 --listen 0.0.0.0:20002 --upstream rabbitmq2:5672
./toxiproxy-cli create C2R3 --listen 0.0.0.0:30002 --upstream rabbitmq3:5672

./toxiproxy-cli create C3R1 --listen 0.0.0.0:10003 --upstream rabbitmq1:5672
./toxiproxy-cli create C3R2 --listen 0.0.0.0:20003 --upstream rabbitmq2:5672
./toxiproxy-cli create C3R3 --listen 0.0.0.0:30003 --upstream rabbitmq3:5672

./toxiproxy-cli create C4R1 --listen 0.0.0.0:10004 --upstream rabbitmq1:5672
./toxiproxy-cli create C4R2 --listen 0.0.0.0:20004 --upstream rabbitmq2:5672
./toxiproxy-cli create C4R3 --listen 0.0.0.0:30004 --upstream rabbitmq3:5672

./toxiproxy-cli create C5R1 --listen 0.0.0.0:10005 --upstream rabbitmq1:5672
./toxiproxy-cli create C5R2 --listen 0.0.0.0:20005 --upstream rabbitmq2:5672
./toxiproxy-cli create C5R3 --listen 0.0.0.0:30005 --upstream rabbitmq3:5672

./toxiproxy-cli create C6R1 --listen 0.0.0.0:10006 --upstream rabbitmq1:5672
./toxiproxy-cli create C6R2 --listen 0.0.0.0:20006 --upstream rabbitmq2:5672
./toxiproxy-cli create C6R3 --listen 0.0.0.0:30006 --upstream rabbitmq3:5672

./toxiproxy-cli create C7R1 --listen 0.0.0.0:10007 --upstream rabbitmq1:5672
./toxiproxy-cli create C7R2 --listen 0.0.0.0:20007 --upstream rabbitmq2:5672
./toxiproxy-cli create C7R3 --listen 0.0.0.0:30007 --upstream rabbitmq3:5672

./toxiproxy-cli create C8R1 --listen 0.0.0.0:10008 --upstream rabbitmq1:5672
./toxiproxy-cli create C8R2 --listen 0.0.0.0:20008 --upstream rabbitmq2:5672
./toxiproxy-cli create C8R3 --listen 0.0.0.0:30008 --upstream rabbitmq3:5672

./toxiproxy-cli create C9R1 --listen 0.0.0.0:10009 --upstream rabbitmq1:5672
./toxiproxy-cli create C9R2 --listen 0.0.0.0:20009 --upstream rabbitmq2:5672
./toxiproxy-cli create C9R3 --listen 0.0.0.0:30009 --upstream rabbitmq3:5672

./toxiproxy-cli create C10R1 --listen 0.0.0.0:10010 --upstream rabbitmq1:5672
./toxiproxy-cli create C10R2 --listen 0.0.0.0:20010 --upstream rabbitmq2:5672
./toxiproxy-cli create C10R3 --listen 0.0.0.0:30010 --upstream rabbitmq3:5672

./toxiproxy-cli create C11R1 --listen 0.0.0.0:10011 --upstream rabbitmq1:5672
./toxiproxy-cli create C11R2 --listen 0.0.0.0:20011 --upstream rabbitmq2:5672
./toxiproxy-cli create C11R3 --listen 0.0.0.0:30011 --upstream rabbitmq3:5672

./toxiproxy-cli create C12R1 --listen 0.0.0.0:10012 --upstream rabbitmq1:5672
./toxiproxy-cli create C12R2 --listen 0.0.0.0:20012 --upstream rabbitmq2:5672
./toxiproxy-cli create C12R3 --listen 0.0.0.0:30012 --upstream rabbitmq3:5672

./toxiproxy-cli create C13R1 --listen 0.0.0.0:10013 --upstream rabbitmq1:5672
./toxiproxy-cli create C13R2 --listen 0.0.0.0:20013 --upstream rabbitmq2:5672
./toxiproxy-cli create C13R3 --listen 0.0.0.0:30013 --upstream rabbitmq3:5672

./toxiproxy-cli create C14R1 --listen 0.0.0.0:10014 --upstream rabbitmq1:5672
./toxiproxy-cli create C14R2 --listen 0.0.0.0:20014 --upstream rabbitmq2:5672
./toxiproxy-cli create C14R3 --listen 0.0.0.0:30014 --upstream rabbitmq3:5672

./toxiproxy-cli create C15R1 --listen 0.0.0.0:10015 --upstream rabbitmq1:5672
./toxiproxy-cli create C15R2 --listen 0.0.0.0:20015 --upstream rabbitmq2:5672
./toxiproxy-cli create C15R3 --listen 0.0.0.0:30015 --upstream rabbitmq3:5672

./toxiproxy-cli create C16R1 --listen 0.0.0.0:10016 --upstream rabbitmq1:5672
./toxiproxy-cli create C16R2 --listen 0.0.0.0:20016 --upstream rabbitmq2:5672
./toxiproxy-cli create C16R3 --listen 0.0.0.0:30016 --upstream rabbitmq3:5672

./toxiproxy-cli create C17R1 --listen 0.0.0.0:10017 --upstream rabbitmq1:5672
./toxiproxy-cli create C17R2 --listen 0.0.0.0:20017 --upstream rabbitmq2:5672
./toxiproxy-cli create C17R3 --listen 0.0.0.0:30017 --upstream rabbitmq3:5672

./toxiproxy-cli create C18R1 --listen 0.0.0.0:10018 --upstream rabbitmq1:5672
./toxiproxy-cli create C18R2 --listen 0.0.0.0:20018 --upstream rabbitmq2:5672
./toxiproxy-cli create C18R3 --listen 0.0.0.0:30018 --upstream rabbitmq3:5672

./toxiproxy-cli create C19R1 --listen 0.0.0.0:10019 --upstream rabbitmq1:5672
./toxiproxy-cli create C19R2 --listen 0.0.0.0:20019 --upstream rabbitmq2:5672
./toxiproxy-cli create C19R3 --listen 0.0.0.0:30019 --upstream rabbitmq3:5672

./toxiproxy-cli create C20R1 --listen 0.0.0.0:10020 --upstream rabbitmq1:5672
./toxiproxy-cli create C20R2 --listen 0.0.0.0:20020 --upstream rabbitmq2:5672
./toxiproxy-cli create C20R3 --listen 0.0.0.0:30020 --upstream rabbitmq3:5672
EOF