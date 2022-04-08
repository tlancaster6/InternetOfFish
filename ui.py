import colorama
import os, sys
import subprocess as sp
if os.path.abspath(os.path.join(os.path.dirname(__file__), 'internet_of_fish')) not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'internet_of_fish'))
from internet_of_fish.modules import utils, ui_helpers, definitions, metadata
from internet_of_fish.modules.utils import finput, bprint
import colorama


opt_dict_1 = {
    1: 'get more information about a project or this device',
    2: 'start a new project',
    3: 'do something with an existing project',
    4: 'upload or download data',
    5: 'analyze an existing video for spawning events',
    6: 'update this device',
    7: 'run a test',
    8: 'start the tutorial',
    9: 'exit user interface'
}

opt_dict_1_1 = {
    1: 'list existing projects on this device',
    2: 'view information about the currently active project',
    3: 'view information about a different project',
    4: 'view resource usage',
}

opt_dict_1_2 = {

}

opt_dict_1_3 = {
    1: 'view the currently active project and its status',
    2: 'resume the currently active project',
    3: 'pause the currently active project',
    4: 'change which project is currently active',
    5: 'end the currently active project and upload all data'
}

opt_dict_1_4 = {
    1: 'upload all project data on this device',
    2: 'upload a specific file or directory',
    3: 'download a project from dropbox'
}

opt_dict_1_5 = {

}

opt_dict_1_6 = {
    1: 'update to the newest version of this repository',
    2: 'update project dependencies',
    3: 'rerun auto-configuration script'
}

blue = colorama.Fore.BLUE

class UI:

    def __init__(self):
        colorama.init(autoreset=True)
        art = utils.import_ascii_art()
        bprint(art['IOF'])
        bprint(art['FISH_SEP'])
        self.welcome()

    def welcome(self):
        bprint('Welcome to the InternetOfFish user interface. To get started, select one of the following options:')
        selection = utils.numerical_choice(opt_dict_1, stepout_option=False)
        if selection == 'get more information about a project or this device':
            self.get_more_info()
        elif selection == 'start a new project':
            self.start_new_project()
        elif selection == 'do something with an existing project':
            self.manipulate_existing()
        elif selection == 'upload or download data':
            self.upload_or_download()
        elif selection == 'check an existing video for spawning events':
            self.analyze_video_for_spawning()
        elif selection == 'update this device':
            self.update_device()
        elif selection == 'run a test':
            self.run_test()
        elif selection == 'start the tutorial':
            self.tutorial()
        elif selection == 'exit user interface':
            bprint('goodbye')
            return
        bprint('returning to main menu')
        self.welcome()

    def start_new_project(self):
        metadata.MetaDataHandler()
        ui_helpers.start_project()
        bprint('project started, returning to the main menu')

    def get_more_info(self):
        selection = utils.numerical_choice(opt_dict_1_1, prompt='select on of the following options')
        if selection == 'list existing projects on this device':
            [print(p) for p in ui_helpers.existing_projects()]
        elif selection == 'view information about the currently active project':
            ui_helpers.print_project_info(ui_helpers.active_project())
        elif selection == 'view information about a different project':
            proj_id = finput('enter project id', options=ui_helpers.existing_projects(), simplify=False)
            ui_helpers.print_project_info(proj_id)
        elif selection == 'view resource usage':
            utils.dict_print(ui_helpers.system_status())
        elif selection == 'return to the previous menu':
            return
        self.get_more_info()

    def manipulate_existing(self):
        selection = utils.numerical_choice(opt_dict_1_3, prompt='select on of the following options')
        if selection == 'view the currently active project and its status':
            proj_id, ctime = ui_helpers.active_project()
            mtime = utils.recursive_mtime(definitions.PROJ_DIR(proj_id))
            print(f'the currently active project is {proj_id}, created {ctime}. Last activity at {mtime}')
        elif selection == 'resume the currently active project':
            ui_helpers.start_project()
            print(f'{ui_helpers.active_project()} has resumed in the background')
        elif selection == 'change which project is currently active':
            proj_id = finput('enter project id', options=ui_helpers.existing_projects(), simplify=False)
            ui_helpers.change_active_proj(proj_id)
            print(f'active project is now {proj_id}')
        elif selection == 'pause the currently active project':
            ui_helpers.pause_project()
            print('pause queued. If the current time is outside of recording hours, this may take up to ten minutes '
                  'to take effect')
        elif selection == 'end the currently active project and upload all data':
            ui_helpers.end_project()
            print('upload running in background. To check if it has finished, select the "list existing projects ..."'
                  ' option from the "get more information ..." submenu, and confirm that it prints nothing. Attempting '
                  'to start a new project before this process finishes is not advised')
        elif selection == 'return to the previous menu':
            return
        self.manipulate_existing()

    def upload_or_download(self):
        selection = utils.numerical_choice(opt_dict_1_4, prompt='select on of the following options')

        if selection == 'upload all project data on this device':
            ui_helpers.start_project()
            ui_helpers.end_project()
            print('upload running in background. To check if it has finished, select the "list existing projects ..."'
                  ' option from the "get more information ..." submenu, and confirm that it prints nothing. Attempting '
                  'to start a new project before this upload process finishes is not advised')

        elif selection == 'upload a specific file or directory':
            path = os.path.abspath(input(blue + 'enter the relative or absolute path to the '
                                                              'file/directory to upload'))
            while not os.path.exists(path):
                path = os.path.abspath(input(blue + 'file/directory not found. please try again, or type '
                                                                  'q to return to the previous menu'))
                if path == 'q':
                    return
            out = ui_helpers.upload(path)
            if out.sderr:
                print(f'Problem while uploading: {out.stderr}')

        elif selection == 'download a file from dropbox':
            path = input(blue + 'enter the full path the the Dropbox file or directory')
            while definitions.CLOUD_HOME_DIR not in path:
                path = input(f'{blue}path should start with {definitions.CLOUD_HOME_DIR}, please try again, '
                             f'or press q to return to the previous menu')
                if path == 'q':
                    return
            out = ui_helpers.download(path)
            if not os.path.exists(path):
                print(f'problem while downloading: {out.stderr}')

        elif selection == 'return to the previous menu':
            return
        self.upload_or_download()

    def analyze_video_for_spawning(self):
        if ui_helpers.active_processes():
            if finput('there appears to be a collection or analysis process already running in the background. Do you'
                     'want to pause it to analyze this video instead? (y, n)', options=['y', 'n']) == 'y':
                ui_helpers.pause_project()
            else:
                bprint('returning to previous menu')
                return

        vid_path = input(blue+'enter the absolute or relative path to a local copy of the video')
        while not os.path.exists(vid_path):
            vid_path = input(blue+'could not find that file. please try again, '
                             'or press q to return to the previous menu')
            if vid_path == 'q':
                return
        ui_helpers.analyze_for_spawning(vid_path)
        print('analysis launched in the background.')

    def update_device(self):
        selection = utils.numerical_choice(opt_dict_1_6)
        if selection == 'update to the newest version of this repository':
            sp.run('cd ~/InternetOfFish && git reset --hard HEAD && git pull')
            print('repository updated')
        elif selection == 'update project dependencies':
            sp.run('cd ~/InternetOfFish && ./bin/install_requirements_worker.sh')
            print('dependencies updated')
        elif selection == 'rerun auto-configuration script':
            sp.run('cd ~/InternetOfFish && ./bin/configure_worker.sh')
            print('configuration complete')
        elif selection == 'return to the previous menu':
            return
        self.update_device()


    def run_test(self):
        pass

    def tutorial(self):
        pass


if __name__ == '__main__':
    ui = UI()

