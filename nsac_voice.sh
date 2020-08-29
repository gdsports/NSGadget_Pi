#!/bin/sh
NSG_HOME="/home/pi/NSGadget_Pi"
while true
do
    ${NSG_HOME}/dspeech | /usr/bin/python3 ${NSG_HOME}/nsac.py
    sleep 1
done
