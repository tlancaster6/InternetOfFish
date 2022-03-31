from internet_of_fish.modules.mptools import ProcWorker
from internet_of_fish.modules import definitions
import os, pathlib, subprocess, glob


class UploaderWorker(ProcWorker):
    MAX_TRIES = 3

    def startup(self):
        """
        called automatically when when the upload process runs. Builds up a list of files to upload, based on
        approximate locations and file extensions. This function can be expanded to upload additional files/file types.
        """
        self.logger.debug('entering UploadWorker.startup')
        self.upload_list = []
        proj_dir = os.path.join(definitions.DATA_DIR, self.metadata['proj_id'])
        self.upload_list.extend(glob.glob(os.path.join(proj_dir, '**', '*.h264')))
        self.upload_list.extend(glob.glob(os.path.join(proj_dir, '**', '*.mp4')))
        self.logger.debug('exiting UploadWorker.startup')

    def main_loop(self):
        """
        While the master shutdown event is unset and there are items left in the upload list, use the main function
        to upload them.
        """
        self.logger.debug('entering UploadWorker.main_loop')
        while (not self.shutdown_event.is_set()) and (len(self.upload_list) > 0):
            item = self.upload_list.pop(0)
            self.main_func(item)
        self.logger.debug('exiting UploadWorker.main_loop')

    def main_func(self, item):
        """
        takes items (file paths) in sequence from the upload_list and either uploads or processes them. If the file has
        a .h264 extension, it is converted to an mp4, and the mp4 added to the end of the upload_list. Otherwise, the
        file is uploaded to Dropbox using rclone. This function will attempt to upload/process a given item
        self.MAX_TRIES number of times before failing, but will not throw an exception that might halt the program.
        :param item: path to file to process/upload. Ideally a full path
        :type item: str
        """
        tries_left = self.MAX_TRIES
        while tries_left:
            if item.endswith('.h264'):
                # if it's a h264, convert it to an mp4
                try:
                    mp4_path = self.h264_to_mp4(item)
                    self.logger.debug(f'converting {item} to {mp4_path}')
                    if mp4_path:
                        self.upload_list.append(mp4_path)
                        break
                    else:
                        self.logger.debug(f'failed to convert {os.path.basename(item)}')
                except Exception as e:
                    self.logger.debug(f'unexpected exception {e}')
            else:
                # otherwise, upload the file and delete the local copy
                try:
                    self.logger.debug(f'uploading {item} to {self.local_to_cloud(item)}')
                    cmnd = ['rclone', 'copyto', item, self.local_to_cloud(item)]
                    out = subprocess.run(cmnd, capture_output=True, encoding='utf-8')
                    if self.exists_cloud(item):
                        self.logger.debug(f'successfully uploaded {item}. deleting local copy')
                        os.remove(item)
                        break
                    else:
                        self.logger.debug(f'failed to upload {os.path.basename(item)}: {out.stderr}')
                except Exception as e:
                    self.logger.debug(f'unexpected exception {e}')
            tries_left -= 1

        else:
            # this else clause should only executes if the while loop exited because it ran out of tries
            # (tries_left = 0). If the loop instead hits a break statement (due to a successful upload or conversion)
            # this clause gets skipped.
            self.logger.warning(f'failed three times to process {os.path.basename(item)}. Moving on')

    def exists_local(self, local_path):
        """
        simple helper function that returns True if a file/directory exists locally, false otherwise
        :param local_path: path to file
        :type local_path: str
        :return: True if local_path exists, false otherwise
        :rtype: bool
        """
        return os.path.exists(local_path)

    def exists_cloud(self, local_path):
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
        cmnd = ['rclone', 'lsf', self.local_to_cloud(local_path)]
        return subprocess.run(cmnd, capture_output=True, encoding='utf-8').stdout != ''

    def local_to_cloud(self, local_path):
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

    def h264_to_mp4(self, h264_path):
        """convert a .h264 video to a .mp4 video
        :param h264_path: path to h264 file
        :type h264_path: str
        :return: path to newly-created mp4 file, or None if the conversion failed
        :rtype: str
        """
        self.logger.debug('entering UploadWorker.h264_to_mp4')
        mp4_path = h264_path.replace('.h264', '.mp4')
        command = ['ffmpeg', '-r', str(definitions.FRAMERATE), '-i', h264_path, '-threads', '1', '-c:v', 'copy', '-r',
                   str(definitions.FRAMERATE), mp4_path]
        out = subprocess.run(command, capture_output=True, encoding='utf-8')
        if (os.path.exists(mp4_path)) and (os.path.getsize(mp4_path) > os.path.getsize(h264_path)):
            self.logger.debug(f'successfully converted {h264_path} to {mp4_path}')
            return mp4_path
        else:
            self.logger.warning(f'failed to convert {os.path.basename(h264_path)}.\n{out.stderr}')
            return None

    def shutdown(self):
        """
        prints some debugging information to the log before the process shuts down, especially if there are unprocessed
        items in the upload_list.
        """
        self.logger.debug('entering UploadWorker.shutdown')
        self.event_q.close()
        if len(self.upload_list) != 0:
            remainder = "\n".join(self.upload_list)
            self.logger.warning(f'exiting upload process, but the following files are still in the upload queue: \n'
                                f'{remainder}')
        else:
            self.logger.info('no more items to upload. UploaderWorker shutting down')
        self.logger.debug('exiting UploadWorker.shutdown')
