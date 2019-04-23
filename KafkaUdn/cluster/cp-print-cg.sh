
#!/bin/bash

CONTAINER_ID=$(docker ps | grep $1 | awk '{ print $1 }')
docker exec -i $CONTAINER_ID /bin/bash <<EOF

kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group $2
kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group $2 --members

EOF

