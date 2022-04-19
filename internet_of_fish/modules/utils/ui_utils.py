import datetime
import os

from internet_of_fish.modules.utils import file_utils
from internet_of_fish.modules import definitions
from internet_of_fish.modules import metadata
from internet_of_fish.modules import runner
from internet_of_fish.modules.utils import gen_utils
import psutil
import re
import datetime as dt
import shutil
import time
import subprocess as sp
import platform
import glob

def check_running_in_screen():
    out = sp.run('echo $TERM', shell=True, capture_output=True, encoding='utf-8')
    return out.stdout.startswith('screen')

def print_summary_log_tail():
    out = sp.run(['tail', os.path.join(definitions.LOG_DIR, 'SUMMARY.log')], capture_output=True, encoding='utf-8')
    print(out.stdout)

def print_selected_log_tail():
    ops = [os.path.splitext(f)[0].lower() for f in os.listdir(definitions.LOG_DIR)]
    selection = gen_utils.finput('enter the name of the log file', options=ops)
    out = sp.run(['tail', os.path.join(definitions.LOG_DIR, f'{selection.upper()}.log')], capture_output=True, encoding='utf-8')
    print(out.stdout)

def new_project(**kwargs):
    metadata.MetaDataHandler(**kwargs)
    print('project created and set as the active project. Select "start the currently active project" from the main '
          'manu to start data collection')

def existing_projects():
    proj_ids = [p for p in os.listdir(definitions.DATA_DIR)]
    json_exists = [os.path.exists(os.path.join(definitions.PROJ_DIR(p), f'{p}.json')) for p in proj_ids]
    return [proj_ids[i] for i in range(len(proj_ids)) if json_exists[i]]


def active_processes():
    processes = []
    for proc in psutil.process_iter():
        cmd = proc.cmdline()
        if proc.pid == os.getpid():
            continue
        if 'python3' in cmd and any([True if re.fullmatch('.*internet_of_fish/.*', c) else False for c in cmd]):
            processes.append(proc)
    return processes


def check_is_running():
    is_running = bool(active_processes())
    print(f'there {"appears" if is_running else "does not appear"} to be a project already running')
    if is_running:
        if gen_utils.finput('do you want to pause the currently running project? (y, n)', options=['y', 'n']) == 'y':
            pause_project()


def active_project():
    json_path, _ = file_utils.locate_newest_json()
    if not json_path:
        return None
    return os.path.splitext(os.path.basename(json_path))[0]


def kill_processes():
    procs = active_processes()
    if not procs:
        return
    for p in procs:
        p.terminate()
    gone, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        p.kill()


def get_system_status():
    status_dict = {
        'current_time': datetime.datetime.now(),
        'cpu_temp': float(psutil.sensors_temperatures()['cpu_thermal'][0].current),
        'disk_usage': float(psutil.disk_usage('/').percent),
        'boot_time': dt.datetime.fromtimestamp(psutil.boot_time()),
        'memory_usage': float(psutil.virtual_memory().percent)
    }
    return status_dict

def get_system_info():
    my_platform = platform.uname()
    info_dict = {
        'node': my_platform.node,
        'system': my_platform.system,
        'release': my_platform.release,
        'machine': my_platform.machine,
        'virtual_memory': f'{psutil.virtual_memory().total/(1000**3)}Gb',
        'effective_disk_size': f'{psutil.disk_usage("/").total/(1000**3)}Gb',
        'cpu_count': psutil.cpu_count()
    }
    return info_dict


def change_active_proj(proj_id):
    json_path = os.path.join(definitions.PROJ_DIR(proj_id), f'{proj_id}.json')
    if not os.path.exists(json_path):
        raise FileNotFoundError
    tmp_json_path = os.path.splitext(json_path)[0] + 'tmp.json'
    shutil.copy(json_path, tmp_json_path)
    os.remove(json_path)
    os.rename(tmp_json_path, json_path)
    print(f'active project is now {proj_id}')


def get_project_metadata(proj_id):
    json_path = os.path.join(definitions.PROJ_DIR(proj_id), f'{proj_id}.json')
    metadata_simple = metadata.MetaDataHandler(new_proj=False, json_path=json_path).simplify(infer_types=False)
    return metadata_simple

def print_project_metadata(proj_id):
    gen_utils.dict_print(get_project_metadata(proj_id))


def print_slack_time(proj_id):
    mtime = gen_utils.recursive_mtime(definitions.PROJ_DIR(proj_id))
    slack_time = (datetime.datetime.now() - mtime).total_seconds()
    print(f'{proj_id} last modified a file {slack_time:.2f} seconds ago')
    return slack_time


def inject_override(event_type: str):
    event_type = event_type.upper()
    if event_type not in runner.EVENT_TYPES:
        print(f'{event_type} is an invalid override. Valid overrides include: {", ".join(runner.EVENT_TYPES)}')
    elif not active_processes():
        print('cannot inject an override when no project is currently running')
    else:
        with open(os.path.join(definitions.HOME_DIR, event_type), 'w') as _:
            pass


def clear_logs():
    for log in glob.glob(os.path.join(definitions.LOG_DIR, '*.log')):
        os.remove(log)


def pause_project():
    tries_left = 3
    while active_processes() and tries_left:
        tries_left -= 1
        print('pausing a project that was already running, please wait')
        inject_override('HARD_SHUTDOWN')
        time.sleep(5)
        if os.path.exists(definitions.PAUSE_FILE):
            os.remove(definitions.PAUSE_FILE)
    kill_processes()


