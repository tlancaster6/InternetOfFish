#!/bin/bash
# update the repository
echo 'updating repository'
cd ~/InternetOfFish
git reset --hard HEAD
git pull
# generate a crontab entry to restart data collection every time the pi reboots
echo 'setting up cron job'
(crontab -l ; echo "@reboot ~/InternetOfFish/bin/unit_scripts/auto_start.sh" ) | sort - | uniq - | crontab -
# copy the special bash alias file into the home directory
echo 'setting up bash aliases'
cp ~/InternetOfFish/bin/system_files/.bash_aliases ~/.bash_aliases
# download credential files
rclone copy cichlidVideo:/BioSci-McGrath/Apps/CichlidPiData/__CredentialFiles/iof_credentials ~/InternetOfFish/credentials
