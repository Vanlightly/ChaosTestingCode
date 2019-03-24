#!/bin/bash

cd ../cluster

echo "CHAOS: Healing partition"
blockade join
echo "CHAOS: Partition healed"