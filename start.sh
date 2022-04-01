#!/bin/bash
echo automatically initiating data collection
cd ~/InternetOfFish
git pull
python3 internet_of_fish/main.py
