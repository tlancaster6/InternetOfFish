from internet_of_fish.modules.mptools import QueueProcWorker
from internet_of_fish.modules.utils import file_utils
import os
import subprocess


class UploaderWorker(QueueProcWorker):

    def main_func(self, target, end_of_proj=False):
        """
        takes items (file paths) in sequence from the upload_list and either uploads or processes them. If the file has
        a .h264 extension, it is converted to an mp4, and the mp4 added to the end of the upload_list. Otherwise, the
        file is uploaded to Dropbox using rclone. This function will attempt to upload/process a given item
        self.MAX_TRIES number of times before failing, but will not throw an exception that might halt the program.
        :param item: path to file to process/upload. Ideally a full path
        :type target: str
        """
        tries_left = self.defs.MAX_TRIES
        while not self.shutdown_event.is_set() and tries_left:
            if target.endswith('.h264'):
                mp4_path = self.h264_to_mp4(target)
                if mp4_path:
                    target = mp4_path
                else:
                    continue
            try:
                self.logger.debug(f'uploading {target} to {file_utils.local_to_cloud(target)}')
                cmnd = ['rclone', 'copyto', target, file_utils.local_to_cloud(target)]
                out = subprocess.run(cmnd, capture_output=True, encoding='utf-8')
                if file_utils.exists_cloud(target):
                    self.logger.debug(f'successfully uploaded {target}')
                    if not target.endswith('.json') or end_of_proj:
                        self.logger.debug(f'deleting {target}')
                        os.remove(target)
                    break
                else:
                    self.logger.debug(f'failed to upload {os.path.basename(target)}: {out.stderr}')
            except Exception as e:
                self.logger.debug(f'unexpected exception {e}')
            tries_left -= 1

        else:
            # this else clause should only executes if the while loop exited because it ran out of tries
            # (tries_left = 0). If the loop instead hits a break statement (due to a successful upload or conversion)
            # this clause gets skipped.
            self.logger.warning(f'failed three times to process {os.path.basename(target)}. Moving on')

    def h264_to_mp4(self, h264_path):
        """convert a .h264 video to a .mp4 video
        :param h264_path: path to h264 file
        :type h264_path: str
        :return: path to newly-created mp4 file, or None if the conversion failed
        :rtype: str
        """
        mp4_path = h264_path.replace('.h264', '.mp4')
        command = ['ffmpeg', '-r', str(self.defs.FRAMERATE), '-i', h264_path, '-threads', '1', '-c:v', 'copy', '-r',
                   str(self.defs.FRAMERATE), mp4_path]
        try:
            out = subprocess.run(command, capture_output=True, encoding='utf-8')
            if os.path.exists(mp4_path):
                if os.path.getsize(mp4_path) > os.path.getsize(h264_path):
                    self.logger.debug(f'successfully converted {h264_path} to {mp4_path}')
                    os.remove(h264_path)
                    return mp4_path
                else:
                    os.remove(mp4_path)
                    raise Exception(out.stderr)
        except Exception as e:
            self.logger.warning(f'failed to convert {os.path.basename(h264_path)}.\n{e}')
        return None

    def shutdown(self):
        """
        prints some debugging information to the log before the process shuts down, especially if there are unprocessed
        items in the upload_list.
        """
        self.event_q.close()
        self.work_q.close()


class EndUploaderWorker(UploaderWorker):
    """identical to UploaderWorker, except that it will delete the json file after uploading it"""

    def main_loop(self):
        self.logger.debug("Entering QueueProcWorker.main_loop")
        while not self.shutdown_event.is_set():
            item = self.work_q.safe_get()
            if not item:
                continue
            self.logger.debug(f"QueueProcWorker.main_loop received '{item}' message")
            if item == "END":
                break
            else:
                self.main_func(item, True)
