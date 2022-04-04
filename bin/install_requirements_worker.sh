#!/bin/bash
# TODO: figure out which dependencies are stricty necessary, particularly wrt openc-cv dependencies
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install libedgetpu1-std
sudo apt-get install python3-pycoral
sudo pip3 install picamera
sudo pip3 install opencv-python-headless
sudo pip3 install ffmpeg
sudo pip3 install -U numpy
sudo apt-get install libatlas-base-dev
#sudo apt-get install libjpeg-dev libpng-dev libtiff-dev
#sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
#sudo apt-get install libxvidcore-dev libx264-dev
#sudo apt-get install libgtk2.0-dev
#sudo apt-get install build-essential cmake pkg-config
