import os, json, sys, re, platform
from internet_of_fish.modules import definitions, utils
from datetime import datetime, date


def flinput(prompt, options=None, simplify=True, match_string=None):
    """formmated looped input"""
    while True:
        user_input = str(input(prompt))
        if simplify:
            user_input = user_input.lower().strip().replace(' ', '')
        if options and user_input not in options:
            print(f'invalid input. valid options are {" ".join(options)}')
        if match_string and not re.match(match_string, user_input):
            print(f'please provide an input formatted as {match_string}')
        elif flinput(f'your input will be recorded as {user_input}. press "y" to accept, "n" to reenter', ['y', 'n']) == 'y':
            return user_input
        else:
            pass


class Item:

    def __init__(self, key, value='NA', prompt=None, options=None, required=True,
                 simplify=True, match_string='.+', help_str=None):
        self.key, self.value, self.options, self.required = key, value, options, required
        self.simplify, self.match_string = simplify, match_string
        self.prompt = prompt if prompt else f'enter a value for {key}'
        self.help_string = help_str if help_str else 'sorry, help string has not been written for this item'

    def confirm_with_user(self):
        if flinput(f'value set automatically to f{self.value}. modify? (y, n)', ['y', 'n']) == 'y':
            self.query_user()

    def query_user(self):
        self.value = flinput(self.prompt, self.options, self.simplify, self.match_string)


class MetaDataDict:

    def __init__(self):
        self.logger = utils.make_logger('METADATA')
        self.item_dict = {
            'owner':       Item(key='item',
                                prompt='enter your initials (first, middle, and last)',
                                match_string='[a-z]{3}'),
            'tank_id':     Item(key='tank_id',
                                value=platform.node().split('-')[-1],
                                prompt='enter the tank id (e.g., t003, t123, t123sv, t123asdf, etc.',
                                match_string='^t\d{3}[a-zA-Z]*'),
            'species':     Item(key='species',
                                prompt='enter the species name or abbreviation thereof'),
            'fish_type':   Item(key='fish_type',
                                prompt='is the a rock, sand, or hybrid tank?',
                                options=['rock', 'sand', 'rocksand', 'other']),
            'n_fish':      Item(key='n_fish',
                                prompt='how many fish are in this tank total? (enter NA to leave blank)',
                                required=False,
                                simplify=False),
            'model_id':    Item(key='model_id',
                                prompt='enter the name of the model you want to use (case sensitive)',
                                options=os.listdir(definitions.MODELS_DIR),
                                simplify=False,
                                required=False),
            'coral_color': Item(key='coral_color',
                                prompt='what color is the coral in this tank?',
                                options=['black', 'white', 'other'],
                                required=False),
            'bower_type':  Item(key='bower_type',
                                prompt='is this a castle or pit species?',
                                options=['castle', 'pit'],
                                required=False),
            'end_date':    Item(key='end_date',
                                prompt='enter a date in ("yyyy-mm-dd" format) when this project should auto-terminate',
                                match_string='^(20)\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])',
                                required=False),
            'notes':       Item(key='notes',
                                prompt='enter any additional notes you want to make on this trial',
                                simplify=False,
                                required=False),
            'created':     Item(key='created'),
            'proj_id':     Item(key='proj_id'),
            'ip_address':  Item(key='ip_address'),
            'json_path':   Item(key='json_path')
        }

    def __getitem__(self, key):
        """once the MetaDataDict object is created, this function allows for it to be used like a traditional dict,
        such that MetaDataDict()['key'] is equivalent to MetaDataDict().item_dict['key'].value"""
        try:
            return eval(self.item_dict[key].value)
        except NameError:
            return self.item_dict[key].value

    def __setitem__(self, key, value):
        """if we have a __getitems__, might as well have a __setitems__"""
        value = str(value)
        if key not in self.item_dict.keys():
            self.logger.warning(f'attempted to set non-existant key {key} in MetaDataDict')
            return
        elif not re.match(self.item_dict[key].match_string, value):
            self.logger.warning(f'attempted to set {key} to {value}, but value did not match {self.item_dict[key].match_string}')
        elif value not in self.item_dict[key].options:
            self.logger.warning(f'attempted to set {key} to {value}, but value was not in {self.item_dict[key].options}')
        else:
            self.item_dict[key].value = value

    def autogen(self):
        self['created'] = datetime.isoformat(datetime.now())
        self['proj_id'] = f'{self["owner"]}_{self["tank_id"]}_{date.today().strftime("%m%d%y")}'
        self['ip_address'] = utils.get_ip()
        self['json_path'] = os.path.join(definitions.DATA_DIR, self['proj_id'], f'{self["proj_id"]}.json')

    def verify(self):
        """loop through the item_dict and check that, if the required flag is set, the value of the item is not 'NA'"""
        missing_keys = []
        for item in self.item_dict.values():
            if item.required and item.value.upper() == 'NA':
                missing_keys.append(item.key)
        if len(missing_keys) != 0:
            self.logger.warning(f'the following metadata items must be set before starting data collection: {missing_keys}')
            return missing_keys
        else:
            self.logger.debug('metadata dictionary verified')
            return True

    def update(self, simple_metadata_dict: dict):
        """for each key,value pair in simple_metadata_dict, find an item in self.item_dict with the same key, and
        update the 'value' attribute of the associated Item object"""
        for key, value in simple_metadata_dict.items():
            self[key] = value

    def simplify(self):
        return {key: self[key] for key in self.item_dict.keys()}


class MetaDataHandler(MetaDataDict):
    """relatively thin wrapper around the MetaDataDict class that mostly handles the startup sequence"""

    def __init__(self, new_proj=True, json_path=None):
        super().__init__()

        if json_path:
            self.json_path = json_path
        elif new_proj:
            self.json_path = self.generate_metadata()
        else:
            self.json_path = self.locate_newest_json()
        self.item_dict.update(self.decode_metadata(self.json_path))


    def decode_metadata(self, json_path):
        with open(json_path, 'r') as f:
            return json.load(f)


    def generate_metadata(self):
        self.logger.info('gathering metadata from user')
        metadict = self.item_dict
        while True:
            # essential queries
            for key in ['owner', 'tank_id', 'species', 'fish_type', ]:
                metadict[key].query_user()

            # case-specific queries
            if self['species_type'] == 'sand':
                metadict['bower_type'].query_user()
            elif self['species_type'] in ['rock', 'rocksand']:
                metadict['coral_color'].query_user()

            # optional queries
            for key in ['model_id', 'n_fish', 'notes']:
                if flinput(f'would you like to set the {key} parameter? (y, n)', ['y', 'n']) == 'y':
                    metadict[key].query_user()

            if flinput('do you want to set an automated end date for this project? (y, n)', ['y', 'n']) == 'y':
                while True:
                    metadict['end_date'].query_user()
                    if not date.fromisoformat(metadict['end']) > date.today():
                        print('the date you entered appears to be in the past. please try again')
                    else:
                        break

            for key, val in self.simplify().items():
                print(f'{key}: {val}')
            if flinput('is the above metadata correct? (type "yes" or "no")', ['yes', 'no']) == 'yes':
                with open(metadict['json_path'], 'w') as f:
                    json.dump(self.simplify(), f)
                    self.logger.info('metadata generated and save to .json file')
                return metadict['json_path']

    def locate_newest_json(self):
        self.logger.info('attempting to locate existing metadata file')
        try:
            potential_projects = next(os.walk(definitions.DATA_DIR))[1]
            potential_jsons = [os.path.join(definitions.DATA_DIR, pp, f'{pp}.json') for pp in potential_projects]
            if len(potential_jsons) == 0:
                raise FileNotFoundError
            else:
                json_path = sorted([pj for pj in potential_jsons if os.path.exists(pj)], key=os.path.getctime)[-1]
                ctime = datetime.fromtimestamp(os.path.getctime(json_path)).isoformat()
                self.logger.info(f'found {os.path.basename(json_path)}, created {ctime}')
                return json_path

        except Exception as e:
            self.logger.debug(e)
            self.logger.info(f'failed to locate an existing metadata file')
            if flinput('failed to locate an existing json file. Do you want to create one? (y, n)', ['y', 'n']) == 'y':
                return self.generate_metadata()
            else:
                self.logger.info(f'user chose to exit program')
                sys.exit()
