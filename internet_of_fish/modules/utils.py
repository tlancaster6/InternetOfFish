import glob
import logging
import re
import time, datetime
from internet_of_fish.modules import definitions
import os, socket
from functools import wraps
from types import FunctionType, SimpleNamespace
import sys
import colorama

LOG_DIR = definitions.LOG_DIR
logging.getLogger('PIL').setLevel(logging.WARNING)

default_color = 'BLUE'
default_style = 'BRIGHT'
summary_logger_level = logging.INFO


def finput(prompt, options=None, simplify=True, pattern=None, mapping=None, help_str=None, confirm=False,
           color=default_color, style=default_style):
    """customized user input function. short for "formatted input", but really I just like that it's a pun on "fin"

    :param prompt: prompt to give the user, identical usage to the builtin input function. Required.
    :type prompt: str
    :param options: list of allowed user inputs. If simplify is true, ensure these are lowercase and without whitespace.
                    If None (default) do not enforce an option set. To allow users to leave the query blank, include
                    an empty string in this list.
    :type options: list[str]
    :param simplify: if True, convert user input to lowercase and remove any whitespaces
    :type simplify: bool
    :param pattern: enforce that the user input matches the given regular expression pattern using re.fullmatch. If None
                    (default) re matching is skipped
    :type pattern: str
    :param mapping: dictionary mapping user inputs to the actual values the function returns. If None (default) user
                    input is returned directly. input loop will repeat until the user enters a value matching a key
                    in the mapping dictionary.
    :type mapping: dict
    :param help_str: if user types "help", this string will be displayed and then the user will be queried again
    :type help_str: str
    :param confirm: if True (default), flinput will loop until the user accepts the formatted version of their input
    :rtype confirm: bool
    :return: formatted and verified user input
    :rtype: str
    """
    while True:
        prompt = prompt.strip(': ') + ':  ' if prompt else prompt
        if prompt:
            cprint(prompt, color, style)
        user_input = input()
        if user_input == 'help':
            print(help_str)
            continue
        if simplify:
            user_input = user_input.lower().strip().replace(' ', '')
        if (options and user_input not in options) or (mapping and user_input not in mapping.keys()):
            print(f'invalid input. valid options are {" ".join(options)}')
            continue
        if pattern and not re.fullmatch(pattern, user_input):
            print(f'pattern mistmatch. please provide an input formatted as {pattern}')
            continue
        if mapping:
            user_input = mapping[user_input]
        if confirm:
            if finput(f'your input will be recorded as {user_input}. press "y" to accept, "n" to reenter',
                      ['y', 'n'], confirm=False) == 'y':
                return user_input
            else:
                continue
        return user_input


def cprint(print_str, color=default_color, style=default_style):
    color = getattr(colorama.Fore, color.upper()) if color else ''
    style = getattr(colorama.Style, style.upper()) if style else ''
    print(color + style + print_str)


def numerical_choice(opt_dict, prompt=None, stepout_option=True, color=default_color, style=default_style):
    print('\n')
    if stepout_option:
        opt_dict = opt_dict.copy()
        opt_dict.update({0: 'return to the previous menu'})
    if prompt:
        cprint(prompt, color, style)
    for key, val in opt_dict.items():
        cprint(f'<{key}>  {val}', color, style)
    options = [str(key) for key in list(opt_dict.keys())]
    selection = finput('', options=options, color=color, style=style)
    print('\n')
    return opt_dict[int(selection)]

def dict_print(dict_: dict, dt_as_iso=True):
    for key, val in dict_.items():
        if isinstance(val, (datetime.datetime, datetime.date, datetime.time)) and dt_as_iso:
            val = val.isoformat()
        print(f'{key}: {val}')

def import_ascii_art():
    with open(os.path.join(definitions.RESOURCES_DIR, 'ascii_art.txt'), 'r') as f:
        ret = f.read().split('\n\n')
        return dict(zip(ret[::2], ret[1::2]))


def freeze_definitions(proj_id, additional_definitions=None):
    defs = {'PROJ_ID': proj_id}
    for setting in dir(definitions):
        if setting.isupper() and not setting.startswith('_'):
            if callable(getattr(definitions, setting)):
                defs.update({setting: getattr(definitions, setting)(proj_id)})
            else:
                defs.update({setting: getattr(definitions, setting)})
    if additional_definitions:
        defs.update(additional_definitions)
    return SimpleNamespace(**defs)


def locate_newest_json():
    try:
        potential_projects = next(os.walk(definitions.DATA_DIR))[1]
    except StopIteration:
        return None
    potential_jsons = [os.path.join(definitions.PROJ_DIR(pp), f'{pp}.json') for pp in potential_projects]
    json_path = sorted([pj for pj in potential_jsons if os.path.exists(pj)], key=os.path.getctime)[-1]
    ctime = datetime.datetime.fromtimestamp(os.path.getctime(json_path)).isoformat()
    return json_path, ctime


def recursive_mtime(path):
    if os.path.isfile(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))
    else:
        paths = glob.glob(os.path.join(path, '**', '*'), recursive=True)
        mtimes = [os.path.getmtime(p) for p in paths]
        try:
            return datetime.datetime.fromtimestamp(max(mtimes))
        except ValueError:
            return datetime.datetime.min

def sleep_secs(max_sleep, end_time=999999999999999.9):
    """see mptools.sleep_secs()"""
    return max(0.0, min(end_time - time.time(), max_sleep))


def current_time_ms():
    """
    get milliseconds since last epoch as an integer. useful for generating unique filenames
    :return: ms since last epoch
    :rtype: int
    """
    return int(round(time.time() * 1000))


def current_time_iso():
    """
    get current date and time in human-readable iso format
    :return: iso formatted datetime
    :rtype: str
    """
    return datetime.datetime.now().isoformat(timespec='seconds')


class DoubleLogger:
    def __init__(self, name):
        self.summary_logger = self.make_logger('SUMMARY', summary_logger_level)
        self.debug_logger = self.make_logger(name.upper(), logging.DEBUG)

    def make_logger(self, name, level):
        fmt = '%(asctime)s %(name)-16s %(levelname)-8s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        fh = logging.FileHandler(os.path.join(definitions.LOG_DIR, f'{name}.log'), mode='a')
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(fh)
        return logger

    def debug(self, msg):
        self.debug_logger.debug(msg)
        self.summary_logger.debug(msg)

    def info(self, msg):
        self.debug_logger.info(msg)
        self.summary_logger.info(msg)

    def warning(self, msg):
        self.debug_logger.warning(msg)
        self.summary_logger.warning(msg)

    def error(self, msg):
        self.debug_logger.error(msg)
        self.summary_logger.error(msg)

    def critical(self, msg):
        self.debug_logger.error(msg)
        self.summary_logger.error(msg)


def make_logger(name):
    """
    generate a logging.Logger object that writes to a file called "{name}.log". Logging level determined by
    definitions.LOG_LEVEL.
    :param name: logger name. Determines the name of the output file, and can also be used to access the logger via
                 logging.getLogger(name)
    :type name: str
    :return: pre-configured logger
    :rtype: logging.Logger
    """
    if not os.path.exists(definitions.LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    logger = DoubleLogger(name)
    return logger


def get_ip():
    """
    get the IP address of the current device.
    :return: device IP
    :rtype: str
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def cleanup(proj_id):
    logfiles = glob.glob(os.path.join(definitions.LOG_DIR, '*.log'))
    logfiles.extend(glob.glob(os.path.join(definitions.PROJ_LOG_DIR(proj_id), '*.log')))
    vidfiles = glob.glob(os.path.join(definitions.PROJ_VID_DIR(proj_id), '*'))
    imgfiles = glob.glob(os.path.join(definitions.PROJ_IMG_DIR(proj_id), '*'))
    allfiles = logfiles + vidfiles + imgfiles
    [os.remove(f) for f in allfiles]


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

# def retry_wrapper():
#     def wrapper_fn(f):
#         @wraps(f)
#         def new_wrapper(*args, **kwargs):
#             for i in range(definitions.MAX_TRIES):
#                 try:
#                     return f(*args, **kwargs)
#                 except Exception as e:
#                     error = e
#             raise error
#         return new_wrapper
#     return wrapper_fn


def strfmt_func_call(fname, *args, **kwargs):
    arg_str = ', '.join([str(arg) for arg in args])
    kwarg_str = ', '.join([f'{key}={val}' for key, val in kwargs.items()])
    all_args_str = ", ".join([arg_str, kwarg_str])
    all_args_str = all_args_str if all_args_str.strip() != ',' else ''
    return f'{fname}({all_args_str})'


def autolog(method):
    @wraps(method)
    def wrapper(self, *method_args, **method_kwargs):
        try:
            logger = self.logger
        except AttributeError:
            return method(self, *method_args, **method_kwargs)
        logger.debug(f'entering {strfmt_func_call(method.__name__, *method_args, **method_kwargs)}')
        result = method(self, *method_args, **method_kwargs)
        logger.debug(f'exiting {method.__name__}')
        return result
    return wrapper


class AutologMetaclass(type):
        def __new__(mcs, classname, bases, classDict):
            newClassDict = {}
            for attributeName, attribute in classDict.items():
                if isinstance(attribute, FunctionType):
                    attribute = autolog(attribute)
                newClassDict[attributeName] = attribute
            return type.__new__(mcs, classname, bases, newClassDict)


class Averager:

    def __init__(self):
        """
        efficient calculation of the mean of a growing dataset

        this lightweight class tracks the current mean (self.avg) and dataset size (self.count) of a growing dataset,
        without storing the entire dataset in memory. Useful, for example, for finding the average runtime of a process
        that repeats an undetermined number of times over a long period (which would otherwise require that we store
        every runtime value in a list or similar container until we were ready to calculate the final mean)
        """
        self.avg = None
        self.count = 0

    def update(self, val):
        """
        update the running mean (self.avg) according to val, and increment the count by one
        :param val: value that is being "appended" to the dataset
        :type val: float
        """
        if self.count == 0:
            self.avg = val
        else:
            self.avg = ((self.avg * self.count) + val) / (self.count + 1)
        self.count += 1


