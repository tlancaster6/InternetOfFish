import os
import cv2


def jpgs_to_mp4(img_paths, dest_dir, fps):
    """create a video from a directory of images

    :param img_paths: list of paths to images that will be combined into an mp4
    :type img_paths: list[str]
    :param dest_dir: folder where the video will go
    :type dest_dir: str
    :param fps: framerate (frames per second) for the new video. Default 10
    :type fps: int
    :return vid_path: path to newly created video
    :rtype: str
    """
    img_paths = sorted(img_paths)
    frame = cv2.imread(img_paths[0])
    height, width, layers = frame.shape
    vid_path = os.path.join(dest_dir, f'{os.path.splitext(os.path.basename(img_paths[0]))[0]}_event.mp4')
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    video = cv2.VideoWriter(vid_path, fourcc, fps, (width, height))
    for img_path in img_paths:
        video.write(cv2.imread(img_path))
    video.release()
    return vid_path
