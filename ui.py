import colorama
from internet_of_fish.modules import definitions, utils
from internet_of_fish.modules.metadata import finput

art = utils.import_ascii_art()
print(colorama.Fore.BLUE + art['IOF'])
print(colorama.Fore.BLUE + art['FISH_SEP'])

opt_dict_1 = {
    1: 'start a new project',
    2: 'terminate and upload an existing project',
    3: 'pause the currently running project',
    4: 'resume a project that was paused or crashed',
    5: 'manually upload data',
    6: 'start the tutorial',
    7: 'run a test',
    8: 'update this device'
}

def numerical_choice(opt_dict, prompt=None):
    if prompt:
        print(prompt)
    for key, val in opt_dict.items():
        print(f'<{key}>  {val}')
    options = [str(key) for key in list(opt_dict.keys())]
    selection = finput('', options=options)
    return opt_dict[int(selection)]


def welcome():
    print('Welcome to the InternetOfFish user interface. To get started, choose one of the following options:')
    selection = numerical_choice(opt_dict_1)
