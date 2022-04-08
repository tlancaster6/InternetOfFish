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


def active_project():
    json_path, ctime = utils.locate_newest_json()
    return os.path.splitext(os.path.basename(json_path))[0], ctime


def kill_processes():
    procs = active_processes()
    if not procs:
        return
    for p in procs:
        p.terminate()
    gone, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        p.kill()


def system_status():
    status_dict = {
        'current_time': datetime.datetime.now(),
        'cpu_temp': float(psutil.sensors_temperatures()['cpu_thermal'][0].current),
        'disk_usage': float(psutil.disk_usage('/').percent),
        'boot_time': dt.datetime.fromtimestamp(psutil.boot_time()),
        'memory_usage': float(psutil.virtual_memory().percent)
    }
    return status_dict


def change_active_proj(proj_id):
    json_path = os.path.join(definitions.PROJ_DIR(proj_id), f'{proj_id}.json')
    if not os.path.exists(json_path):
        raise FileNotFoundError
    tmp_json_path = os.path.splitext(json_path)[0] + 'tmp.json'
    shutil.copy(json_path, tmp_json_path)
    os.remove(json_path)
    os.rename(tmp_json_path, json_path)


def start_project(proj_id=None):
    if active_processes():
        pause_project()
    if not proj_id or proj_id != active_project():
        change_active_proj(proj_id)
    kwargs = {'stdin': sp.PIPE, 'stdout': sp.PIPE, 'stderr': sp.PIPE, 'start_new_session': True}
    return sp.Popen(['python3', 'internet_of_fish/main.py'], **kwargs)


def analyze_for_spawning(vid_path):
    kwargs = {'stdin': sp.PIPE, 'stdout': sp.PIPE, 'stderr': sp.PIPE, 'start_new_session': True}
    return sp.Popen(['python3', 'internet_of_fish/main.py', '-s', vid_path], **kwargs)


def get_project_metadata(proj_id):
    json_path = os.path.join(definitions.PROJ_DIR(proj_id), f'{proj_id}.json')
    metadata_simple = metadata.MetaDataHandler(json_path=json_path).simplify(infer_types=False)
    return metadata_simple


def get_slack_time(proj_id):
    mtime = utils.recursive_mtime(definitions.PROJ_DIR(proj_id))
    return (datetime.datetime.now() - mtime).total_seconds()


def pause_project():
    tries_left = 3
    while active_processes() and tries_left:
        tries_left -= 1
        print('pausing existing project, please wait')
        with open(definitions.PAUSE_FILE, 'w') as _:
            pass
        time.sleep(5)
        if os.path.exists(definitions.PAUSE_FILE):
            os.remove(definitions.PAUSE_FILE)
    kill_processes()


def end_project():
    if active_processes():
        with open(definitions.END_FILE, 'w') as _:
            pass


def print_project_info(proj_id):
    slack_time = get_slack_time(proj_id)
    utils.dict_print(get_project_metadata(proj_id))
    print(f'{proj_id} appears to be {"running" if slack_time < 600 else "paused"}')


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
