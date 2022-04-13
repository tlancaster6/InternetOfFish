#!/bin/bash
echo automatically initiating data collection
cd ~/InternetOfFish
git reset --hard HEAD
git pull
screen -dm -S master bash -c "python3 internet_of_fish/ui.py --autostart"
