import datetime
import os
import pathlib
import subprocess as sp
import json

from internet_of_fish.modules import definitions


def locate_newest_json():
    try:
        potential_projects = next(os.walk(definitions.DATA_DIR))[1]
    except StopIteration:
        return None, None
    potential_jsons = [os.path.join(definitions.PROJ_DIR(pp), f'{pp}.json') for pp in potential_projects]
    json_path = sorted([pj for pj in potential_jsons if os.path.exists(pj)], key=os.path.getctime)[-1]
    ctime = datetime.datetime.fromtimestamp(os.path.getctime(json_path)).isoformat()
    return json_path, ctime


def remove_empty_dirs(parent_dir, remove_root=False):
    if not os.path.isdir(parent_dir):
        return
    children = os.listdir(parent_dir)
    if children:
        for child in children:
            fullpath = os.path.join(parent_dir, child)
            if os.path.isdir(fullpath):
                remove_empty_dirs(fullpath, remove_root=True)
    children = os.listdir(parent_dir)
    if not children and remove_root:
        os.rmdir(parent_dir)


def create_project_tree(proj_id):
    for dir_func in [definitions.PROJ_DIR,
                     definitions.PROJ_IMG_DIR,
                     definitions.PROJ_VID_DIR,
                     definitions.PROJ_LOG_DIR]:
        path = dir_func(proj_id)
        if not os.path.exists(path):
            os.makedirs(path)


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


def download(cloud_path=None):
    if not cloud_path:
        rel = input(f'complete the below path stub to indicate the location of the file:'
                           f'\n{definitions.CLOUD_HOME_DIR}/')
        cloud_path = os.path.join(definitions.CLOUD_HOME_DIR, rel)
    else:
        rel = os.path.relpath(cloud_path, definitions.CLOUD_HOME_DIR)
    local_path = str(pathlib.PurePosixPath(definitions.HOME_DIR) / pathlib.PurePath(rel))
    if not os.path.exists(os.path.dirname(local_path)):
        os.makedirs(os.path.dirname(local_path))
    print('downloading, please wait')
    if os.path.splitext(local_path)[1]:
        # if it's a file:
        out = sp.run(['rclone', 'copy', cloud_path, os.path.dirname(local_path)], capture_output=True, encoding='utf-8')
    else:
        # if it's a directory:
        out = sp.run(['rclone', 'copy', cloud_path, local_path], capture_output=True, encoding='utf-8')
    if out.stderr:
        print(f'download error: {out.stderr}')
    else:
        print('download complete')
    return out


def download_json(proj_id=None):
    if not proj_id:
        proj_id = input('enter the project id:  ')
        while not exists_cloud(definitions.PROJ_JSON_FILE(proj_id)):
            print('invalid project id, please try again')
            proj_id = input('enter the project id:  ')
    local_json_path = definitions.PROJ_JSON_FILE(proj_id)
    download(local_to_cloud(local_json_path))
    with open(local_json_path, 'r') as f:
        source = json.load(f)['source']
        if source and source != 'None':
            print(f'json specifies source as {source}. Downloading')
            download(local_to_cloud(source))
    return local_json_path


def exists_cloud(local_path):
    """
    simple helper function that returns True if a file exists on Dropbox, false otherwise. May behave strangely if
    local_path is a directory rather than file. For consistency with other class methods, this function expects
    a path to a local file, which it then converts to a corresponding cloud path using the self.local_to_cloud
    method. It is not, however, necessary for the local file to actually exist for this function to be used.
    :param local_path: path to local file
    :type local_path: str
    :return: True if local_path exists, false otherwise
    :rtype: bool
    """
    cmnd = ['rclone', 'lsf', local_to_cloud(local_path)]
    return sp.run(cmnd, capture_output=True, encoding='utf-8').stdout != ''


def local_to_cloud(local_path):
    """
    takes a path to a local file or directory and converts it to a Dropbox location. This is done by replacing
    definitions.HOME_DIR with definitions.CLOUD_HOME_DIR.
    :param local_path: path to a local file. Note: file must be somewhere in the current user's home directory.
    :type local_path: str
    :return: path to corresponding file or directory on Dropbox
    :rtype: str
    """
    rel = os.path.relpath(local_path, definitions.HOME_DIR)
    cloud_path = pathlib.PurePosixPath(definitions.CLOUD_HOME_DIR) / pathlib.PurePath(rel)
    return str(cloud_path)

def exists_local(local_path):
    """
    simple helper function that returns True if a file/directory exists locally, false otherwise
    :param local_path: path to file
    :type local_path: str
    :return: True if local_path exists, false otherwise
    :rtype: bool
    """
    return os.path.exists(local_path)
