#!/bin/sh
lxterminal
cd wallofjoco
while :
do
  echo Starting up
  sudo rfkill block 2
  sudo hciconfig hci0 down
  sudo hciconfig hci0 up
  echo Running the wall
  ./wallofjoco.py &
  sleep 30
  sudo rfkill unblock 2
  echo Resetting NFC
  ./resetnfc.py
  echo Running trinket control
  ./trinketctl.py
  pkill wallofjoco.py
  sleep 10
done
echo Bye

