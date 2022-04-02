#!/bin/bash
# generate a crontab entry to restart data collection every time the pi reboots
(crontab -l ; echo "@reboot ~/InternetOfFish/bin/unit_scripts/auto_start.sh" ) | sort - | uniq - | crontab -
# update the repository
cd ~/InternetOfFish
git pull
# copy the special bash alias file into the home directory
cp ~/InternetOfFish/internet_of_fish/bin/system_files/.bash_aliases ~/.bash_aliases
