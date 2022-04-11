#!/bin/bash
# TODO: figure out which dependencies are stricty necessary, particularly wrt openc-cv dependencies
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install libedgetpu1-std
sudo apt-get -y install python3-pycoral
curl https://rclone.org/install.sh | sudo bash
sudo apt-get -y install screen
sudo pip3 install rclone
sudo pip3 install picamera
sudo pip3 install sendgrid
sudo pip3 install opencv-python-headless
sudo pip3 install ffmpeg
sudo pip3 install -U numpy
sudo apt-get -y install libatlas-base-dev
