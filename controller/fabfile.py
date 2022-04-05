from fabric import Connection, Config
from fabric import task
from capturer import CaptureOutput
import subprocess
import os

"""
This file helps simplify repetitive tasks that involve ssh'ing into multiple pi's. It requires two files to work:
1) InternetOfFish/credentials/hosts.secret, which contains the IP addresses of the target pi's, one per line
2) InternetOfFish/credentials/pi_password.secret, containing the password shared by all pi's on the host list 
Note that these files (and for that matter, the InternetOfFish repository as a whole) only needs to be installed on the
computer you are using to reach the pi's, and not on the pi's themselves. 

The first time you use this interface, you may also need to install the required libraries. To do so, navigate to
InternetOfFish/bin and run the install_requirements_controller.sh script.

To use the fab commads defined here, open up a terminal on any computer that is either hardwired to the GaTech network
or connected via VPN. Navigate to this file's parent directory, InternetOfFish/controller. You should now be able to 
run the following commands, to the described effect:

COMMAND        | EFFECT 
-----------------------------------------------------------------------------------------------------------------
fab ping       | ping each host and show which ones are reachable
fab listhosts  | list which hosts have been loaded from hosts.secret
fab config     | configure all hosts. This will ensure the InternetOfFish repo is present and up-to-date on each pi, 
               | install the necessary dependencies, and perform a few setup tasks. This command can also be used to 
               | fully update a set of hosts after a major change in the repository. Running it on a pi that is fully
               | configured and up-to-date has no effect
fab pull       | run "git pull" on every host to update the InternetOfFish repository. This only works for hosts that
               | have already been configured
"""

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CODE_DIR)
CREDENTIALS_DIR = os.path.join(ROOT_DIR, 'credentials')
HOST_FILE = os.path.join(CREDENTIALS_DIR, 'hosts.secret')
CREDENTIAL_FILE = os.path.join(CREDENTIALS_DIR, 'pi_password.secret')

HOME_DIR = os.path.expanduser('~')
PI_USER = 'pi'

if os.path.exists(CREDENTIAL_FILE):
    print('loading pi password from credentials.txt')
    with open(CREDENTIAL_FILE, 'r') as f:
        PI_PASSWORD = f.read().strip()
else:
    PI_PASSWORD = input('enter pi password')
    if input('save password? (y/n)') == 'y':
        with open(CREDENTIAL_FILE, 'w+') as f:
            f.write(PI_PASSWORD)

with open(HOST_FILE) as f:
    MY_HOSTS = [line.strip() for line in f]
    MY_HOSTS = [{
        'host': f"{PI_USER}@{ip}",
        "connect_kwargs": {"password": PI_PASSWORD},
    } for ip in MY_HOSTS]


@task
def listhosts(c):
    print(MY_HOSTS)


@task(hosts=MY_HOSTS)
def ping(c):
    _status = ['UP', 'UNREACHABLE']

    with CaptureOutput(relay=False):
        if subprocess.call(["ping", "-q", "-c", "1", c.host]) == 0:
            return_value = 0
        else:
            return_value = 1

    print("{host} is {status}".format(host=c.host, status=_status[return_value]))

    return return_value

@task(hosts=MY_HOSTS)
def pull(c):
    print(f'Pulling to {c.host}')
    try:
        with c.cd('/home/pi/InternetOfFish'):
            c.run('git reset --hard HEAD')
            c.run('git pull')
    except Exception as e:
        print(f'pull failed: {e}')


@task(hosts=MY_HOSTS)
def config(c):
    print(f'configuring {c.host}')
    try:
        with c.cd('/home/pi/'):
            if c.run('test -d {}'.format('InternetOfFish'), warn=True).failed:
                print('cloning repo')
                c.run('git clone https://github.com/tlancaster6/InternetOfFish')
            print('running configure_worker.sh')
            c.run('chmod u+x InternetOfFish/bin/configure_worker.sh')
            c.run('InternetOfFish/bin/configure_worker.sh')

    except Exception as e:
        print(f'config failed with error: {e}')


