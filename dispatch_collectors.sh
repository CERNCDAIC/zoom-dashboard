#!/bin/bash

pids=()

echo flask live-events --debug --meeting --past  --interval 10 
flask live-events --debug --meeting --past  --interval 10 &
pids[0]=$!
sleep $((1 + $RANDOM % 120))
echo flask live-events --debug --meeting   --interval 1 
flask live-events --debug --meeting --interval 1 &
pids[1]=$!
sleep $((1 + $RANDOM % 120))
echo flask live-events --debug  --interval 2
flask live-events --debug   --interval 2 &
pids[2]=$!
sleep $((1 + $RANDOM % 120))
echo flask live-events --debug  --past  --interval 15 
flask live-events --debug  --past  --interval 15 &
pids[3]=$!

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done