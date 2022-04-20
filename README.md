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

        bash ./bin/configure_controller.sh
4) Using nano, open the file called InternetOfFish/credentials/hosts.secret, or create it if it does not exist. In this
file, enter the IP addresses of the pi(s) you want to reach, one per line.
5) Move into the directory InternetOfFish/controller. Ping the pi's listed in the host file using the following command,
and confirm that they are all able to connect.  

        fab ping
6) Run the automated configuration process using the following command. This will clone this repository into the home
directory of each pi, install all dependencies, and modify some elements of the system configuration. This process will
take a while, especially the part where numpy gets recompiled. If you are configuring multiple pi's, and are in a
hurry, you can also ssh into each pi individually and manually run the configure_worker.sh script (located in the 
project bin)

        fab config
7) Double check that the repository was cloned successfully and is fully up-to-date using the following command. This
command can also be run any time the main repository is updated to update all pi's on the host list.

        fab pull

### Starting your first project
Begin by either ssh'ing into your pi remotely, or connecting a keyboard and monitor to interface with it directly.
Start a screen session with the command  

       screen -S master
Now run the following command to enter the interactive InternetOfFish command-line interface:

        iof
From the main menu, select  

        create a new project
Then from the submenu that opens, select 

        create a standard project
to enter the interactive project creation process. Answer the prompts as they appear until you are returned to the 
menu where you selected "create a standard project". Choose option 0, 

        return to the previous menu, 
to return to the main menu. At this point, the project framework has been generated, but data collection has not yet 
started. You can confirm this  by selecting "check if a project is already running" from the main menu. If, however, 
you instead select "show the currently active project", you should see the project that you just created. This 
highlights the distinction between an "active" project and a "running" project, which is explained in further 
detail later. To run the project you just created, select the option marked

        start the currently active project
You should see a message indicating that the project is now running in the background. At this point, it is safe to 
detach the screen (by pressing ctrl+a then ctrl+d) and log out of the pi.

### Active project vs. Running project
As mentioned in the last section, the terms "active" and "running" 