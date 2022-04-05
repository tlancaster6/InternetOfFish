# InternetOfFish
Python package for running video collection and on-device real-time computer vision analysis on Raspbery 
Pi computers in the Streelman/McGrath aquatics facility

### Setup and Installation:  
1) Assemble one or more Raspberry Pis and equip them with SD cards containing a fresh install of the Raspberry Pi OS.
At this time, the coral TPU only support Debian 10 derivatives, so you need to use the legacy Raspberry Pi OS built on 
Debian Buster. Set up the pi(s) in the aquatics facility, making sure to attach the Coral USB TPU accelerator and 
connect the ethernet.
2) On any computer hardwired to the GaTech network, or connected to it via VPN, open a terminal. Clone this repository 
using the command:  

        git clone https://github.com/tlancaster6/InternetOfFish
3) Move into the newly-created InternetOfFish directory and run the following command to install the controller
dependencies.  

        ./bin/install_requirements_controller.sh
4) Using nano, open the file called InternetOfFish/credentials/hosts.secret, or create it if it does not exist. In this
file, enter the IP addresses of the pi(s) you want to reach, one per line.
5) Move into the directory InternetOfFish/controller. Ping the pi's listed in the host file using the following command,
and confirm that they are all able to connect.  

        fab ping
6) Run the automated configuration process using the following command. This will clone this repository into the home
directory of each pi, install all dependencies, and modify some elements of the system configuration.

        fab config
7) Double check that the repository was cloned successfull and is fully up-to-date using the following command. This
command can also be run any time the main repository is updated to update all pi's on the host list.

        fab pull

### Starting data collection for the first time

