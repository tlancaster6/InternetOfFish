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

### Built-in Aliases
To make some of the more common tasks easier to execute, this package ships with a custom .bash_aliases file with the
following aliases predefined. These can be run from anywhere on the pi -- no need to move into a particular directory.  

        alias iof-update='cd ~/InternetOfFish && git pull' 
        alias iof-new="python3 ~/InternetOfFish/internet_of_fish/main.py -n"
        alias iof-resume="python3 ~/InternetOfFish/internet_of_fish/main.py"
        alias iof-test="python3 ~/InternetOfFish/internet_of_fish/main.py -t 60"
        alias iof-end="touch ~/END"
These aliased commands will have the following effects:  
* iof-update: updates to the latest version of the InternetOfFish repo  
* iof-new: set up a new project interactively and start data collection  
* iof-resume: resume the most recently running project. Only works if the project is already configured (using iof-new)
and has not been cleared from the pi (as happens after an iof-end call)  
* iof-test: puts the pi into stress testing mode, causing it to cycle between the passive and active modes once every 
two minutes, instead of once every 24 hours. This mode is not meant for normal data collection, and requires an existing
metadata to funciton properly.
* iof-end: stop data collection, upload everything, and delete the project from this pi. This command is the best way to
to terminate a project that is running in the background, as occurs when the auto_start.sh script runs. All local data
from the project will be deleted after it successfully uploads, so only run this command if you are ready to end the
project, as you will no longer be able to resume it the iof-resume command.

To test if these aliases are working, try running the following command:  

        iof-update
You should see some output print indicating either that the repository has been updated, or that it was already up to
date. If, instead, you get a "command not found" error, double check that the file ~/.bash_aliases matches the lines
given above. If it does, try restarting your terminal so that they take effect.

### Starting a new project
Begin by either ssh'ing into your pi remotely, or connecting a keyboard and monitor to interface with it directly. Make
sure that the repo is up to date using the command:
        
        iof-update
Start a screen session with the command  

       screen
Now run the following command to enter the interactive setup process:

        iof-new
Answer the questions as they appear on the screen to generate the project metadata, as shown in the image below
![alt text](https://github.com/tlancaster6/InternetOfFish/blob/tucker_dev/resources/metadata_input_example.png?raw=true)
Once you answer "yes" to the final question, data collection will start immediately (or in the morning, if outside of
the daylight hours defined in definitions.py). Detach the screen session by pressing ctrl+a then ctrl+d. 

### Checking in on a project that is running
If you recently started a project, you should be able to check in on it by running

      screen -r
This will re-attach the screen you used when you first created the project, where you should see informational messages
occasionally printing to the terminal.  

If running screen -r fails to find a detached screen, that does not necessarily mean that the project has halted.
Wherever possible, this application errs on the side of keeping itself running. As part of that, during the intial
configuration, it adds a cronjob to the system's crontab that essentially call iof-resume every time the pi starts up. 
If the application encounters a fatal error, it will force the pi to reboot, and when the pi boots up it will attempt
to pick up data collection where it left off. This is intended to automate the all-to-common scenario where some 
intermittent issue can be solved just be rebooting the pi. A side effect of this behavior, however, is that the
application will resume in the background, where you can no longer peek in on it using screen -r. For now, the easiest
way to confirm that such a project is still running is to open one of the debugging logs 
(located in InternetOfFish/logs) and confirm that the timestamp on the most recent logging message is no more than a few
seconds old (HINT: to skip to the end of the logfile, open it with nano and press ctrl+w then ctrl+v).

### Ending a project
When you are ready to end a project (for example, to start a new one), run the following command in the terminal from
any location.

      iof-end

This creates an empty file called ~/END. Every few seconds, the application checks if this file exists. If it does, it 
switches to end-mode. In this mode, it will upload any data present in the ~/CichlidPiData folder and then delete
the local copy. It is very important to run this command before starting a new project, as it is the best way to 
shut down any sneaky background instance of the application that started automatically when the pi booted up.
