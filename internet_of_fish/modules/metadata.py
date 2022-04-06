import os, json, sys, re, platform, time
from internet_of_fish.modules import definitions, utils
import datetime as dt
from typing import Union, Callable, Type
from types import SimpleNamespace

my_regexes = SimpleNamespace()
my_regexes.any_int = r'\d+'
my_regexes.any_float = r'[0-9]*\.?[0-9]+'
my_regexes.any_float_less_than_1 = r'0*?\.[0-9]+'
my_regexes.any_int_less_than_24 = r'([01]?[0-9]|2[0-3])'
my_regexes.any_iso_date = r'\d\d\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])'
my_regexes.any_iso_time = r'([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
my_regexes.any_iso_datetime = r'{}T{}'.format(my_regexes.any_iso_date, my_regexes.any_iso_time)
my_regexes.any_email = r'.+@.+\.(com|edu|org)'
my_regexes.any_tank_id = r't\d{3}[a-zA-Z]*'
my_regexes.any_movie = r'.+\.(mp4|h264)'
my_regexes.any_bool = r'[tT]rue|[fF]alse'
my_regexes.any_null = r'[Nn][Oo][Nn][Ee]|[Nn][Uu][Ll][Ll]|'
 

def finput(prompt, options=None, simplify=True, pattern=None, mapping=None, help_str=None, confirm=False):
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
        prompt = prompt.strip(': ') + ':  '
        user_input = str(input(prompt))
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
            else: continue
        return user_input


class MetaDataDictBase(metaclass=utils.AutologMetaclass):

    def __init__(self, name: str):
        """dict-like class that holds a collection of MetaValue objects with various preset attributes, as well as
        a few useful utility functions.

        The MetaDataDict.contents houses the full dictionary of MetaValue objects, where each key in
        MetaDataDict.contents matches the MetaValue.key attribute of the paired associated MetaValue object.
        In practice, this class can be used much like a traditional dictionary by using square-bracket notation,
        as MetaDataDict()[key] will return MetaDataDict().contents[key].value, and MetaDataDict()[key]=val will set
        MetaDataDict().contents[key].value to val (with some caveats -- see __setitem__ and __getitem__ methods).

        :param name: identifier used to set the name of the log file
        :type name: str
        """
        self.name = name
        self.logger = utils.make_logger(name)
        self.contents = {}

    def __getitem__(self, key):
        """once the MetaDataDict object is created, this function allows for it to be used like a traditional dict,
        such that MetaDataDict()['key'] is equivalent to MetaDataDict().contents['key'].value. Also makes it such
        that, when MetaValue.value is a callable function, MetaDataDict[key] returns the evaluation result
        of the callable instead. This ensures, for example, that the value of self['proj_id'] will always reflect
        modifications to self['owner'] and self['tank_id']. While, internally, each MetaValue.value is stored
        as a string, callable that returns a string, or (possibly nested) dict-like collection of strings, this method
        recognizes when the value can be converted to a float, int, bool, datetime.date, datetime.time,
        datetime.datetime, or NoneType object and returns it as such"""
        retval = self.contents[key].value
        if isinstance(retval, dict):
            return retval
        if isinstance(retval, MetaDataDictBase):
            return retval.simplify()
        if callable(retval):
            return str(retval())
        if re.fullmatch(my_regexes.any_bool, retval):
            return eval(retval.title())
        if re.fullmatch(my_regexes.any_float, retval):
            return eval(retval)
        if re.fullmatch(my_regexes.any_null, retval):
            return None
        if re.fullmatch(my_regexes.any_iso_date, retval):
            return dt.date.fromisoformat(retval)
        if re.fullmatch(my_regexes.any_iso_time, retval):
            return dt.time.fromisoformat(retval)
        if re.fullmatch(my_regexes.any_iso_datetime, retval):
            return dt.datetime.fromisoformat(retval)
        return str(retval)

    def __setitem__(self, key, value):
        """if we have a __getitems__, might as well have a __setitems__. slightly stricter than the base dict
        equivalent (for example, does not allow setting of an item for which a key does not already exist.)"""
        value = str(value)
        if key not in self.contents.keys():
            self.logger.warning(f'attempted to set non-existant key {key} in MetaDataDict')
        elif re.fullmatch(my_regexes.any_null, value):
            self.contents[key].value = 'None'
        elif self.contents[key].pattern and not re.match(self.contents[key].pattern, value):
            self.logger.warning(f'attempted to set {key} to {value}, but value did not match {self.contents[key].pattern}')
        elif self.contents[key].options and value not in self.contents[key].options:
            self.logger.warning(f'attempted to set {key} to {value}, but value was not in {self.contents[key].options}')
        else:
            self.contents[key].value = value

    def verify(self):
        """loop through the contents and check that, if the required flag is set, the value of the item is not 'None'"""
        missing_keys = []
        for item in self.contents.values():
            if item.required and item.value == 'None':
                missing_keys.append(item.key)
        if len(missing_keys) != 0:
            self.logger.warning(f'the following metadata items must be set before starting'
                                f' data collection: {missing_keys}')
            return missing_keys
        else:
            self.logger.debug('metadata dictionary verified')
            return True

    def quick_update(self, simple_metadata_dict: dict):
        """for each key,value pair in simple_metadata_dict, find an item in self.contents with the same key, and
        update the 'value' attribute of the associated Item object. Note that the values in simple_metadata_dict
        must have the __str__ magic method defined"""
        for key, value in simple_metadata_dict.items():
            self[key] = str(value)

    def simplify(self, infer_types=True):
        """return a simple dict composed of {MetaValue.key: MetaValue.value} for each MetaValue in self.contents
        if MetaValue.Value is itself derived from the MetaDataDictBase class, the __getitem__ behavior will cause
        this method to be called recursively until the return value is a nested dict of simple objects"""
        if infer_types:
            return {key: self[key] for key in self.contents.keys()}
        else:
            return {key: self.contents[key].value for key in self.contents.keys()}


    def keys(self):
        return list(self.contents.keys())

    def items(self):
        return list(self.simplify().items())

    def values(self):
        return list(self.simplify().values())

class MetaValue:

    def __init__(self, key, value: Union[str, Callable[[], str], dict, MetaDataDictBase] = 'None', prompt=None,
                 options=None, required=True, simplify=True, pattern='.*', mapping=None, help_str=None):
        """data container for MetaDataDict entries that includes information required query the user about the value
        and enforce various conditions on the value

        :param key: short descriptor, used as a dict key when constructing a dictionary of MetaValue objects. Required
        :type key: str
        :param value: core piece of data being stored, or a Callable that returns a piece of core data. Default "None"
        :type value: Union[str, dict, Callable[[], str]]
        :param prompt: custom prompt for querying the user. Defaults to f'enter a value for {key}'. see flinput
        :type prompt: str
        :param options: list of allowed user inputs. see flinput
        :type options: list[str]
        :param required: if True (default) this MetaValue is required for any functional usage of the class instance
        :type required: bool
        :param simplify: if True (default) format user input (see flinput for details)
        :type simplify: bool
        :param pattern: see flinput. Defaults to '.*', i.e., pretty much anything
        :type pattern: str
        :param mapping: see flinput. Defaults to None
        :type mapping: dict
        :param help_str: any additional case-specific usage details go here
        :type help_str: str
        """
        self.key, self.value, self.options, self.required = key, value, options, required
        self.simplify, self.pattern, self.mapping = simplify, pattern, mapping
        self.prompt = prompt if prompt else f'enter a value for {key}'
        self.help_string = '\n'.join([f'{key}: {val}' for key, val in self.__dict__.items()] + [str(help_str)])

    def confirm_with_user(self):
        """show the user the current self.value, ask if they want to change it, and call query_user if so"""
        val = self.value() if callable(self.value) else self.value
        if finput(f'value of {self.key} set automatically to {val}. is this correct? (y, n)', ['y', 'n']) == 'n':
            self.query_user()

    def query_user(self):
        """set self.value based on user input by calling flinput with current the promp, options, simplify, and pattern
        attributes of MetaValue"""
        self.value = finput(self.prompt, self.options, self.simplify, self.pattern, self.mapping, self.help_string)
        if self.value == '':
            self.value = 'None'


class AdvancedConfigDict(MetaDataDictBase):

    def __init__(self):
        super().__init__('METADATA')
        self.contents = {
            'MAX_DETS':
                MetaValue(key='MAX_DETS',
                          value='5',
                          pattern=my_regexes.any_int,
                          help_str='maximum number of fish detections that should be returned. Ignored if n_fish is'
                                   'specified during metadata creation'),
            'CONF_THRESH':
                MetaValue(key='CONF_THRESH',
                          value='0.4',
                          pattern=my_regexes.any_float_less_than_1,
                          help_str='detector score threshold'),
            'INTERVAL_SECS':
                MetaValue(key='INTERVAL_SECS',
                          value='0.5',
                          pattern=my_regexes.any_float,
                          help_str='time between image captures in seconds'),
            'HIT_THRESH_SECS':
                MetaValue(key='HIT_THRESH_SECS',
                          value='5',
                          pattern=my_regexes.any_int,
                          help_str='approximate number of seconds of activity before an event should be registered'),
            'IMG_BUFFER_SECS':
                MetaValue(key='IMG_BUFFER_SECS',
                          value='30',
                          pattern=my_regexes.any_int,
                          help_str='length of video, in seconds, that will be saved when a hit occurs'),
            'START_HOUR':
                MetaValue(key='START_HOUR',
                          value='8',
                          pattern=my_regexes.any_int_less_than_24,
                          help_str='daily collection start time. e.g., set to 8 to start at 8am'),
            'END_HOUR':
                MetaValue(key='END_HOUR',
                          value='18',
                          pattern=my_regexes.any_int_less_than_24,
                          help_str='daily collection end time. e.g., set to 19 to end at 7pm'),
            'MAX_VIDEO_LEN_SECS':
                MetaValue(key='MAX_VIDEO_LEN_SECS',
                          value='3600',
                          pattern=my_regexes.any_int,
                          help_str='max length, in seconds, of individual videos. '
                                   'Set to 100000 to disable video splitting'),
            'MIN_NOTIFICATION_INTERVAL':
                MetaValue(key='MIN_NOTIFICATION_INTERVAL',
                          value='600',
                          pattern=my_regexes.any_int,
                          help_str='cooldown time, in seconds, between notifications'),
            'H_RESOLUTION':
                MetaValue(key='H_RESOLUTION',
                          value='1296',
                          pattern=my_regexes.any_int,
                          help_str='picamera horizontal resolution'),
            'V_RESOLUTION':
                MetaValue(key='V_RESOLUTION',
                          value='972',
                          pattern=my_regexes.any_int,
                          help_str='picamera vertical resolution'),
            'FRAMERATE':
                MetaValue(key='FRAMERATE',
                          value='30',
                          pattern=my_regexes.any_int,
                          help_str='picamera framerate'),
            'BOT_EMAIL':
                MetaValue(key='BOT_EMAIL',
                          value='themcgrathlab@gmail.com',
                          pattern=my_regexes.any_email,
                          help_str='email address that has been configured with sendgrid to serve notifications'),
            'MAX_UPLOAD_WORKERS':
                MetaValue(key='MAX_UPLOAD_WORKERS',
                          value='3',
                          pattern=my_regexes.any_int,
                          help_str='max number of simultaneous upload processes to spawn'),
            'MAX_TIRES':
                MetaValue(key='MAX_TIRES',
                          value='3',
                          pattern=my_regexes.any_int,
                          help_str='max number of times to retry various failure-prone operations'),
            'DEFAULT_STARTUP_WAIT_SECS':
                MetaValue(key='DEFAULT_STARTUP_WAIT_SECS',
                          value='10',
                          pattern=my_regexes.any_float,
                          help_str='default time to wait for a process to start before raising an error'),
            'DEFAULT_SHUTDOWN_WAIT_SECS':
                MetaValue(key='DEFAULT_SHUTDOWN_WAIT_SECS',
                          value='10',
                          pattern=my_regexes.any_float,
                          help_str='default time to wait for a process to shut down normally before '
                                   'force-terminating it'),
        }


class MetaDataDict(MetaDataDictBase):

    def __init__(self):
        super().__init__('METADATA')
        self.contents = {
            'owner':       MetaValue(key='owner',
                                     prompt='enter your initials (first, middle, and last)',
                                     pattern='[a-z]{3}'),
            'email':       MetaValue(key='email',
                                     prompt='enter your email address',
                                     pattern=my_regexes.any_email),
            'tank_id':     MetaValue(key='tank_id',
                                     value=platform.node().split('-')[-1].lower(),
                                     prompt='enter the tank id (e.g., t003, t123, t123sv, t123asdf, etc.',
                                     pattern=my_regexes.any_tank_id),
            'species':     MetaValue(key='species',
                                     prompt='enter the species name or abbreviation thereof'),
            'fish_type':   MetaValue(key='fish_type',
                                     prompt='is the a rock, sand, or hybrid tank?',
                                     options=['rock', 'sand', 'rocksand', 'other']),
            'n_fish':      MetaValue(key='n_fish',
                                     prompt='how many fish are in this tank total? (press enter to leave blank)',
                                     required=False,
                                     simplify=False),
            'model_id':    MetaValue(key='model_id',
                                     prompt='enter the name of the model you want to use (press enter to leave blank)',
                                     options=os.listdir(definitions.MODELS_DIR) + [''],
                                     simplify=False,
                                     required=False),
            'coral_color': MetaValue(key='coral_color',
                                     prompt='what color is the coral in this tank?',
                                     options=['black', 'white', 'other'],
                                     required=False),
            'bower_type':  MetaValue(key='bower_type',
                                     prompt='is this a castle or pit species?',
                                     options=['castle', 'pit'],
                                     required=False),
            'end_date':    MetaValue(key='end_date',
                                     value=dt.date.isoformat(dt.date.max),
                                     prompt='enter a date ("yyyy-mm-dd" format) when this project will auto-terminate',
                                     pattern=my_regexes.any_iso_date),
            'end_time':     MetaValue(key='end_time',
                                      value=dt.time.isoformat(dt.time.max, 'seconds'),
                                      pattern=my_regexes.any_iso_time),
            'notes':       MetaValue(key='notes',
                                     prompt='enter any additional notes you want to make on this trial, '
                                            'or press enter to leave blank',
                                     simplify=False,
                                     required=False),
            'created':     MetaValue(key='created',
                                     value=utils.current_time_iso(),
                                     pattern=my_regexes.any_iso_datetime),
            'ip_address':  MetaValue(key='ip_address',
                                     value=utils.get_ip()),
            'kill_after':  MetaValue(key='kill_after',
                                     pattern=my_regexes.any_int,
                                     required=False,
                                     help_str='if set, the project will attempt to terminate after the given number of '
                                              'seconds. Used mostly for testing'),
            'source':      MetaValue(key='source',
                                     pattern=my_regexes.any_movie,
                                     required=False,
                                     help_str='path to source video, for analyzing an '
                                              'existing video instead of the camera input'),
            'testing':     MetaValue(key='testing',
                                     value='False',
                                     required=False),
            'advanced_config': MetaValue(key='advanced_config',
                                         value=AdvancedConfigDict())
        }

        # add a few special MetaValue objects that generate their values dynamically
        created_shortform = self["created"].strftime("%m%d%y")
        self.contents.update({
            'proj_id':   MetaValue(key='proj_id',
                                   value=lambda: f'{self["owner"]}_{self["tank_id"]}_{self["species"]}'
                                                 f'_{created_shortform}'),
            'json_path': MetaValue(key='json_path',
                                   value=lambda: os.path.join(definitions.PROJ_DIR(self['proj_id']),
                                                              f'{self["proj_id"]}.json'))
        })



class MetaDataHandler(MetaDataDict):

    def __init__(self, new_proj=True, json_path=None, **kwargs):
        """
        relatively thin wrapper around the MetaDataDict class that mostly handles the startup sequence for
        user-initialization or automated initialization of project-specific values.
        :param new_proj: if True (default) program will query user for project-specific parameters. If False and
                         json_path=None, it will attempt to read the most recently created json file in the data
                         directory. If json_path is specified, this argument is ignored.
        :type new_proj: bool
        :param json_path: forces the MetaDataHandler to use the specified json file
        :type json_path: str
        :param **kwargs: additional keyword arguments are passed directly to self.quick_update
                         (see MetaDataDict.quick_update)
        """
        super().__init__()
        self.quick_update(kwargs)
        if json_path:
            self.json_path = json_path
            if new_proj:
                self.logger.warning('MetaDataHandler instantiated with both new_project=True and json_path specified. '
                                    'Ignoring new_project=True')
        elif new_proj:
            self.json_path = self.generate_metadata()
        else:
            self.json_path = self.locate_newest_json()
        md = self.decode_metadata(self.json_path)
        md.update(kwargs)
        self.quick_update(md)
        self.set_kill_condition()
        utils.create_project_tree(self['proj_id'])
        self.definitions = utils.freeze_definitions(self['advanced_config'])
        self.verify()

    def decode_metadata(self, json_path):
        """read a metadata json file"""
        with open(json_path, 'r') as f:
            return json.load(f)

    def generate_metadata(self):
        """gather project-specific metadata from the user"""
        self.logger.info('gathering metadata from user')
        time.sleep(0.1)
        contents = self.contents
        print('the program will now ask you a series of questions in order to generate the metadata json file for \n'
              'this project. At any time, you may type "help" for additional details about a particular parameter\n')
        while True:
            # essential queries
            for key in ['owner', 'email', 'species', 'fish_type']:
                contents[key].query_user()

            # conditional queries
            if self['fish_type'] == 'sand':
                contents['bower_type'].query_user()
            elif self['fish_type'] in ['rock', 'rocksand']:
                contents['coral_color'].query_user()

            # optional, but non-conditional queries
            for key in ['model_id', 'n_fish', 'notes']:
                contents[key].query_user()

            # special queries
            if self['kill_after'] != 'None':
                if finput('do you want to set an automated end date for this project? (y, n)', ['y', 'n']) == 'y':
                    while True:
                        contents['end_date'].query_user()
                        if not self['end_date'] > dt.date.today():
                            print('the date you entered appears to be in the past. please try again')
                        else:
                            break
                    self['end_time'] = dt.time.isoformat(dt.time.max, 'seconds')

            # confirm some of the autogenerated values with the user
            print("\nyou will now be asked to confirm a few parameters that were generated automatically. "
                  "Note that modifying these values may cause unexpected behavior\n")
            for key in ['tank_id', 'proj_id', 'ip_address']:
                contents[key].confirm_with_user()

            # edit the advanced config if desired
            if finput('edit advanced config? (y, n)', options=['y', 'n']) == 'y':
                self.edit_advanced_config()
                print('exiting advanced configuration')

            # print out the complete metadata for a final confirmation
            print('\n')
            for key, val in self.simplify().items():
                if key != 'advanced_config':
                    print(f'{key}: {val}')
            while finput('is the above metadata correct? (type "yes" or "no")', ['yes', 'no']) == 'no':
                self.modify_by_key(self)
                for key, val in self.simplify().items():
                    if key != 'advanced_config':
                        print(f'{key}: {val}')

            utils.create_project_tree(self['proj_id'])
            with open(self['json_path'], 'w') as f:
                json.dump(self.simplify(infer_types=False), f)
                self.logger.info('metadata generated and saved to .json file')
            return self['json_path']
            
    def edit_advanced_config(self):
        print('current settings:')
        for key, val in self['advanced_config'].items():
            print(f'{key}: {val}')
        self.modify_by_key(self.contents['advanced_config'].value)
        print('\nadvanced config is now:')
        for key, val in self['advanced_config'].items():
            print(f'{key}: {val}')
        while finput('is the above configuration correct? (type "yes" or "no")', ['yes', 'no']) == 'no':
            print('re-entering advanced config')
            self.edit_advanced_config()

    def modify_by_key(self, mdd: MetaDataDictBase):
        prompt = '\ntype the name of the value you want to modify, or type q to finish'
        options = mdd.keys() + ['q']
        while True:
            user_input = finput(prompt=prompt, options=options, simplify=False)
            if user_input == 'q':
                break
            mdd.contents[user_input].query_user()
        
    def locate_newest_json(self):
        """locate the most recently created json file in the data dir (see definitions.py for data dir location)"""
        self.logger.info('attempting to locate existing metadata file')
        try:
            potential_projects = next(os.walk(definitions.DATA_DIR))[1]
            potential_jsons = [os.path.join(definitions.PROJ_DIR(pp), f'{pp}.json') for pp in potential_projects]
            if len(potential_jsons) == 0:
                raise FileNotFoundError
            else:
                json_path = sorted([pj for pj in potential_jsons if os.path.exists(pj)], key=os.path.getctime)[-1]
                ctime = dt.datetime.fromtimestamp(os.path.getctime(json_path)).isoformat()
                self.logger.info(f'found {os.path.basename(json_path)}, created {ctime}')
                return json_path

        except Exception as e:
            self.logger.debug(e)
            self.logger.info(f'failed to locate an existing metadata file. Create one by running main.py with the'
                             f' --new_proj flag')
            sys.exit()

    def overwrite_json(self):
        with open(self['json_path'], 'w') as f:
            json.dump(self.simplify(infer_types=False), f)
            self.logger.info('json file overwritten with new metadata')

    def set_kill_condition(self):
        if not self['kill_after']:
            start = self['created'].timestamp()
            end = start + float(self['kill_after'])
            self['end_date'], self['end_time'] = dt.datetime.isoformat(
                dt.datetime.fromtimestamp(end), timespec='seconds').split('T')
        elif not self['end_date']:
            self['end_date'], self['end_time'] = dt.datetime.isoformat(
                dt.datetime.max, timespec='seconds').split('T')
        elif not self['end_time']:
            self['end_time'] = dt.time.isoformat(dt.time.max, 'seconds')





