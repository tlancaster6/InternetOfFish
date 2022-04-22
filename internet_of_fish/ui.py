"""this script represents the primary user entry-point to the InternetOfFish (IOF) application. It can be run
like a standard python script using "python3 internet_of_fish/ui.py", or by using the alias command "iof" that
was added to the .bash_aliases file during configuration"""

import os, sys
if os.path.abspath(os.path.dirname(os.path.dirname(__file__))) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from internet_of_fish.modules.utils import gen_utils, ui_utils, file_utils
from internet_of_fish.modules import metadata
from internet_of_fish.modules import mptools
from internet_of_fish.modules import runner
import colorama
from typing import Callable, Any
colorama.init(autoreset=True)


class Opt:

    def __init__(self, opt_str, action, *args, **kwargs):
        """
        low-level building block class of the custom ui, representing a single 'option' that the user can select
        :param opt_str: user-facing description of the option/action
        :type opt_str: str
        :param action: callable that will be executed when the user chooses the option
        :type action: Callable
        :param args: additional positional args that will be passed to the "action" callable. These args can in turn
        be callables that expect no arguments, in which case they will be evaluated before being passed to the
        "action" callable
        :type args: Any
        :param kwargs: additional keyword args that will be passed to the "action" callable. These kwargs can in turn
        be callables that expect no arguments, in which case they will be evaluated before being passed to the
        "action" callable
        :type kwargs: Any
        """
        self.opt_str, self.action, self.args, self.kwargs = opt_str, action, args, kwargs

    def execute(self):
        """call the callable associated with the 'action' parameter, passing through args and kwargs if specified."""
        try:
            args = (arg if not callable(arg) else arg() for arg in self.args)
            kwargs = {key: val if not callable(val) else val() for (key, val) in self.kwargs.items()}
            self.action(*args, **kwargs)
        except Exception as e:
            print(f'failed to execute "{self.opt_str}" with error {e}')



class OptDict:

    def __init__(self, prompt=None, stepout_opt=True):
        """
        class used to store and manipulate collection of Opt objects. Individual OptDict instances form the framework
        of individual user-facing menus
        :param prompt: text that will be displayed above the menu presented to the user. defaults to  'select one of the
            following options'
        :type prompt: str
        :param stepout_opt: whether or not to include an option to "return to the previous menu" as option 0. Can be
            set to False to allow for custom step-out behavior, such as exiting the program gracefully if the user
            steps out of the main menu
        :type stepout_opt: bool
        """
        self.stepout_opt = stepout_opt
        self.prompt = prompt if prompt else 'select one of the following options'
        self.opts = {'0': Opt('return to the previous menu', None)} if stepout_opt else {}

    def update(self, opt):
        """
        add a new option (Opt object) to the OptDict
        :param opt: option to add
        :type opt: Opt
        """
        self.opts.update({str(len(self.opts)): opt})

    def keys(self):
        """
        get the keys of the OptDict.opts dictionary as strings
        :return: list of OptDict.opts keys (usually sequential integers), converted to strings
        :rtype: list[str]
        """
        return [str(key) for key in self.opts.keys()]

    def query(self):
        """
        present the options to the user, query their selection, and either execute the associated 'action', or return
        the the previous menu (if Opt.stepout_opt == True and the user selects 0).
        """
        while True:
            gen_utils.cprint(self.prompt)
            for key, val in self.opts.items():
                gen_utils.cprint(f'<{key}>  {val.opt_str}')
            selection = gen_utils.finput('selection:  ', options=self.keys())
            if selection == '0' and self.stepout_opt:
                break
            else:
                self.opts[selection].execute()


class UI:

    def __init__(self, autostart=False):
        """
        core class for mediating user-program interactions
        :param autostart: if True, the program effectively select 'start the currently active project' from the main
            menu at startup, before handing control back to the user. Allows for the program to restart collection
            without user input, in certain situations.
        :type autostart: bool
        """
        self.main_ctx = None
        self.check_startup_conditions()
        self.welcome()
        self.menus = self.init_menus()
        self.main_menu = self.menus['main_menu']
        if autostart:
            self.start_project()
        self.main_menu.query()

    def init_menus(self):
        """
        generate and populate the OptDict objects that form the functional backbones of the various menus and submenus.
        :return: dictionary containing each OptDict object, keyed by short descriptors of the menus they represent
        :rtype: dict[str, OptDict]
        """
        project_info_menu = OptDict()
        project_info_menu.update(Opt('show the currently active project', print, ui_utils.active_project))
        project_info_menu.update(Opt('view active project\'s parameters/metadata', ui_utils.print_project_metadata,
                                     ui_utils.active_project))
        project_info_menu.update(Opt('check when the active project last modified a file', ui_utils.print_slack_time,
                                     ui_utils.active_project))
        project_info_menu.update(Opt('view the tail of the summary log', ui_utils.print_summary_log_tail))
        project_info_menu.update(Opt('view the tail of a different log', ui_utils.print_selected_log_tail))

        device_info_menu = OptDict()
        device_info_menu.update(Opt('view system info', gen_utils.dict_print, ui_utils.get_system_info))
        device_info_menu.update(Opt('view system status', gen_utils.dict_print, ui_utils.get_system_status))

        new_project_menu = OptDict()
        new_project_menu.update(Opt('create a standard project', ui_utils.new_project))
        new_project_menu.update(Opt('create a demo project', ui_utils.new_project, demo=True))
        new_project_menu.update(Opt('create a test project', ui_utils.new_project, test=True))

        demo_menu = OptDict()
        demo_menu.update(Opt('view the tail of the summary log', ui_utils.print_summary_log_tail))
        demo_menu.update(Opt('view the tail of a different log', ui_utils.print_selected_log_tail))
        demo_menu.update(Opt('trigger the "hit" response', ui_utils.inject_override, 'MOCK_HIT'))
        demo_menu.update(Opt('put the runner into active mode', ui_utils.inject_override, 'ENTER_ACTIVE_MODE'))
        demo_menu.update(Opt('put the runner into passive mode', ui_utils.inject_override, 'ENTER_PASSIVE_MODE'))
        demo_menu.update(Opt('put the runner into end mode', ui_utils.inject_override, 'ENTER_END_MODE'))
        demo_menu.update(Opt('trigger the fatal error response', ui_utils.inject_override, 'FATAL'))

        utils_menu = OptDict()
        utils_menu.update(Opt('enter demo mode', self.enter_demo_mode))
        utils_menu.update(Opt('get info about this device', device_info_menu.query))
        utils_menu.update(Opt('pause the currently running project without exiting', ui_utils.pause_project))
        utils_menu.update(Opt('download a file or directory from dropbox', file_utils.download))
        utils_menu.update(Opt('download the .json file for a particular project', file_utils.download_json))
        utils_menu.update(Opt('clear the log files', ui_utils.clear_logs))

        main_menu = OptDict(stepout_opt=False)
        main_menu.update(Opt('exit the application', self.goodbye))
        main_menu.update(Opt('create a new project', new_project_menu.query))
        main_menu.update(Opt('check if a project is already running', ui_utils.check_is_running))
        main_menu.update(Opt('show the currently active project', print, ui_utils.active_project))
        main_menu.update(Opt('start the currently active project', self.start_project))
        main_menu.update(Opt('get additional info about the currently active project', project_info_menu.query))
        main_menu.update(Opt('change the currently active project', self.change_active_project))
        main_menu.update(Opt('upload all data from this device and delete local copies', self.end_project))
        main_menu.update(Opt('view additional utilities', utils_menu.query))

        return {'main_menu': main_menu, 'new_project_menu': new_project_menu, 'device_info_menu': device_info_menu,
                'project_info_menu': project_info_menu, 'demo_menu': demo_menu, 'utils_menu': utils_menu}

    def check_startup_conditions(self):
        """
        confirm that the startup conditions (currently, just that the program is running in a screen) are met, and exit
        the program if not.
        """
        if not ui_utils.check_running_in_screen():
            print('this application must be run in a screen session. Please start a session with "screen -S master" and'
                  'and restart the application')
            sys.exit()

    def welcome(self):
        """
        print the InternetOfFish header text
        """
        art = gen_utils.import_ascii_art()
        gen_utils.cprint(art['IOF'])
        gen_utils.cprint(art['FISH_SEP'])

    def start_project(self):
        """
        start the currently active project as an independent process. If another project is already running, pause it.
        """
        ui_utils.pause_project()
        if not ui_utils.active_project():
            print('cannot start a project that does not exist. Try selecting "create a new project" instead')
            return
        self.main_ctx = mptools.MainContext(metadata.MetaDataHandler(new_proj=False).simplify())
        mptools.init_signals(self.main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        self.main_ctx.Proc('RUN', runner.RunnerWorker, self.main_ctx)
        print(f'{self.main_ctx.metadata["proj_id"]} is now running in the background')

    def enter_demo_mode(self):
        """
        enter the "demo" menu if the currently running project is marked as demo, otherwise print a warning.
        """
        if self.main_ctx and self.main_ctx.metadata['demo']:
            self.menus['demo_menu'].query()
        else:
            print('please start a project flagged as demo before entering demo mode')

    def change_active_project(self):
        """
        change the currently active project to another valid project already on the device
        """
        change_project_menu = OptDict(prompt='select which project you want to activate')
        for proj in ui_utils.existing_projects():
            change_project_menu.update(Opt(proj, ui_utils.change_active_proj, proj))
        change_project_menu.query()

    def goodbye(self):
        """
        exit the application gracefully
        """
        ui_utils.pause_project()
        if self.main_ctx:
            self.main_ctx.__exit__('', '', '')
        gen_utils.cprint('\ngoodbye')
        sys.exit()
        
    def end_project(self):
        """
        enter end mode, which will upload and delete local copies of all project data on the device
        """
        active_project = ui_utils.active_project()
        if not active_project:
            print('cannot find a project to upload')
            return
        if not ui_utils.active_processes():
            print(f'starting {active_project} in end mode')
            self.start_project()
        ui_utils.inject_override('ENTER_END_MODE')
        print('end mode override injected. Upload will run in background. Do not exit the app or attempt to start'
              'a new project until "upload complete. exiting" prints to the screen')
        
        
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--autostart', action='store_true',
                        help='equivalent to starting the ui and immediately choosing "start the currently active '
                             'project" from the main menu. Used primarily to start the application programmatically')
    args = parser.parse_args()
    ui = UI(autostart=args.autostart)



