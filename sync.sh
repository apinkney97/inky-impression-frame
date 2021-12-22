#!/bin/bash
HOSTS="pi-frame-0 pi-frame-1"
for host in $HOSTS
do
    rsync -av framerunner $host:
done