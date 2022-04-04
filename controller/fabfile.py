from fabric import Connection, Config
from fabric import task
from capturer import CaptureOutput
import subprocess
import os

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(CODE_DIR, 'resources')
HOST_FILE = os.path.join(RESOURCES_DIR, 'hosts.secret')
CREDENTIAL_FILE = os.path.join(RESOURCES_DIR, 'credentials.secret')

HOME_DIR = os.path.expanduser('~')
PI_USER = 'pi'

if os.path.exists(CREDENTIAL_FILE):
    print('loading pi password from credentials.txt')
    with open(CREDENTIAL_FILE, 'r') as f:
        PI_PASSWORD = f.read().strip()
else:
    PI_PASSWORD = input('enter pi password')
    if input('save password? (y/n)') == 'y':
        with open(CREDENTIAL_FILE, 'w') as f:
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
            c.run('git pull')
    except Exception as e:
        print(f'pull failed: {e}')

@task(hosts=MY_HOSTS)
def start(c):
    c.cd("/home/pi/InternetOfFish")
    c.run('python3 internet_of_fish/main.py')

@task(hosts=MY_HOSTS)
def config(c):
    print(f'configuring {c.host}')
    try:
        with c.cd('/home/pi/'):
            if c.run('test -d {}'.format('InternetOfFish'), warn=True).failed:
                print('cloning repo')
                c.run('git clone https://github.com/tlancaster6/InternetOfFish')
            print('running configure_worker.sh')
            c.run('InternetOfFish/bin/configure_worker.sh')

    except Exception as e:
        print(f'config failed with error: {e}')


