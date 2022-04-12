import datetime
import os
from internet_of_fish.modules import definitions, metadata, runner, mptools, utils
from internet_of_fish.main import main
import psutil
import re
import datetime as dt
import shutil
import time
import subprocess as sp
import pathlib
import socket
import sys
import platform


def check_running_in_screen():
    out = sp.run('echo $TERM', shell=True, capture_output=True, encoding='utf-8')
    return out.stdout.startswith('screen')

def print_summary_log_tail():
    out = sp.run(['tail', os.path.join(definitions.LOG_DIR, 'SUMMARY.log')], capture_output=True, encoding='utf-8')
    print(out.stdout)


def existing_projects():
    proj_ids = [p for p in os.listdir(definitions.DATA_DIR)]
    json_exists = [os.path.exists(os.path.join(definitions.PROJ_DIR(p), f'{p}.json')) for p in proj_ids]
    return [proj_ids[i] for i in range(len(proj_ids)) if json_exists[i]]


def active_processes():
    processes = []
    for proc in psutil.process_iter():
        cmd = proc.cmdline()
        if 'python3' in cmd and any([True if re.fullmatch('.*internet_of_fish.*', c) else False for c in cmd]):
            processes.append(proc)
    return processes


def check_is_running():
    is_running = bool(active_processes())
    print(f'there {"appears" if is_running else "does not appear"} to be a project already running')
    if is_running:
        if utils.finput('do you want to pause the currently running project? (y, n)', options=['y', 'n']) == 'y':
            pause_project()


def active_project():
    json_path, _ = utils.locate_newest_json()
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


def start_project(proj_id=None):
    if not proj_id:
        proj_id = active_project()[0]
    if active_processes():
        pause_project()
    if not proj_id or proj_id != active_project()[0]:
        change_active_proj(proj_id)
    kwargs = {'stdin': sp.PIPE, 'stdout': sp.PIPE, 'stderr': sp.PIPE, 'start_new_session': True}
    return sp.Popen(['python3', 'internet_of_fish/main.py'], **kwargs)


def analyze_for_spawning(vid_path):
    kwargs = {'stdin': sp.PIPE, 'stdout': sp.PIPE, 'stderr': sp.PIPE, 'start_new_session': True}
    return sp.Popen(['python3', 'internet_of_fish/main.py', '-s', vid_path], **kwargs)


def get_project_metadata(proj_id):
    json_path = os.path.join(definitions.PROJ_DIR(proj_id), f'{proj_id}.json')
    metadata_simple = metadata.MetaDataHandler(new_proj=False, json_path=json_path).simplify(infer_types=False)
    return metadata_simple

def print_project_metadata(proj_id):
    utils.dict_print(get_project_metadata(proj_id))


def print_slack_time(proj_id):
    mtime = utils.recursive_mtime(definitions.PROJ_DIR(proj_id))
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

def end_project():
    inject_override('ENTER_END_MODE')


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


def upload(local_path):
    rel = os.path.relpath(local_path, definitions.HOME_DIR)
    cloud_path = str(pathlib.PurePosixPath(definitions.CLOUD_HOME_DIR) / pathlib.PurePath(rel))
    if os.path.isfile(local_path):
        out = sp.run(['rclone', 'copy', local_path, os.path.dirname(cloud_path)], capture_output=True, encoding='utf-8')
    elif os.path.isdir(local_path):
        out = sp.run(['rclone', 'copy', local_path, cloud_path], capture_output=True, encoding='utf-8')
    else:
        return None
    return out


def download(cloud_path):
    rel = os.path.relpath(cloud_path, definitions.CLOUD_HOME_DIR)
    local_path = str(pathlib.PurePosixPath(definitions.HOME_DIR) / pathlib.PurePath(rel))
    if os.path.splitext(local_path)[1]:
        out = sp.run(['rclone', 'copy', cloud_path, os.path.dirname(local_path)], capture_output=True, encoding='utf-8')
    else:
        out = sp.run(['rclone', 'copy', cloud_path, local_path], capture_output=True, encoding='utf-8')
    return out


def upload_all():
    pause_project()
    upload(definitions.DATA_DIR)
