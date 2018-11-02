# Kafka Chaos Code

## IP Address Warning
The Kafka code still depends on providing visibility among nodes by modifying the hosts file in each container. I have since started using Blockade's UDN feature which avoids the needs this technique. Until I update the Kafka code, the IP address of the three nodes are assuymed to be 172.17.0.3, 172.17.0.4 and 172.17.0.5 and so if you run the code and the IP addresses are not the same for you then this code will fail.

I'll update the Kafka code to use the UDN feature and automatically detect IP addresses in the future. The Pulsar and RabbitMqUdn folders already use the UDN feature.

## Container images
"blockade up" does not download the images, so make sure you have downloaded them via other means before running any code.
