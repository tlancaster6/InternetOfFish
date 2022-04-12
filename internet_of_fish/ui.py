import os, sys
if os.path.abspath(os.path.dirname(os.path.dirname(__file__))) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from internet_of_fish.modules import ui_helpers, utils, metadata, mptools, runner
import colorama, time
colorama.init(autoreset=True)


class Opt:

    def __init__(self, opt_str, action, *args, **kwargs):
        self.opt_str, self.action, self.args, self.kwargs = opt_str, action, args, kwargs

    def execute(self):
        try:
            args = (arg if not callable(arg) else arg() for arg in self.args)
            kwargs = {key: val if not callable(val) else val() for (key, val) in self.kwargs.items()}
            self.action(*args, **kwargs)
        except Exception as e:
            print(f'failed to execute "{self.opt_str}" with error {e}')



class OptDict:

    def __init__(self, prompt=None, stepout_opt=True):
        self.stepout_opt = stepout_opt
        self.prompt = prompt if prompt else 'select one of the following options'
        self.opts = {'0': Opt('return to the previous menu', None)} if stepout_opt else {}

    def update(self, opt):
        self.opts.update({str(len(self.opts)): opt})

    def keys(self):
        return [str(key) for key in self.opts.keys()]

    def query(self):
        while True:
            utils.cprint(self.prompt)
            for key, val in self.opts.items():
                utils.cprint(f'<{key}>  {val.opt_str}')
            selection = utils.finput('selection:  ', options=self.keys())
            if selection == '0' and self.stepout_opt:
                break
            else:
                self.opts[selection].execute()


class UI:

    def __init__(self):
        self.main_ctx = None
        self.check_startup_conditions()
        self.welcome()
        self.menus = self.init_menus()
        self.main_menu = self.menus['main_menu']
        self.main_menu.query()

    def init_menus(self):
        project_info_menu = OptDict()
        project_info_menu.update(Opt('show the currently active project', print, ui_helpers.active_project))
        project_info_menu.update(Opt('view active project\'s parameters/metadata', ui_helpers.print_project_metadata,
                                     ui_helpers.active_project))
        project_info_menu.update(Opt('check when the active project last modified a file', ui_helpers.print_slack_time,
                                     ui_helpers.active_project))

        device_info_menu = OptDict()
        device_info_menu.update(Opt('view system info', utils.dict_print, ui_helpers.get_system_info))
        device_info_menu.update(Opt('view system status', utils.dict_print, ui_helpers.get_system_status))

        new_project_menu = OptDict()
        new_project_menu.update(Opt('create a standard project', metadata.MetaDataHandler))
        new_project_menu.update(Opt('create a demo project', metadata.MetaDataHandler, demo=True))
        new_project_menu.update(Opt('create a testing project', metadata.MetaDataHandler, testing=True))

        demo_menu = OptDict()
        demo_menu.update(Opt('view the tail of the summary log', ui_helpers.print_summary_log_tail))
        demo_menu.update(Opt('trigger the "hit" response', ui_helpers.inject_override, 'MOCK_HIT'))
        demo_menu.update(Opt('put the runner into active mode', ui_helpers.inject_override, 'ENTER_ACTIVE_MODE'))
        demo_menu.update(Opt('put the runner into passive mode', ui_helpers.inject_override, 'ENTER_PASSIVE_MODE'))
        demo_menu.update(Opt('put the runner into end mode', ui_helpers.inject_override, 'ENTER_END_MODE'))

        main_menu = OptDict(stepout_opt=False)
        main_menu.update(Opt('exit the application', self.goodbye))
        main_menu.update(Opt('create a new project', new_project_menu.query))
        main_menu.update(Opt('check if a project is already running', ui_helpers.check_is_running))
        main_menu.update(Opt('show the currently active project', print, ui_helpers.active_project))
        main_menu.update(Opt('start the currently active project', self.start_project))
        main_menu.update(Opt('get additional info about the currently active project', project_info_menu.query))
        main_menu.update(Opt('change the currently active project', self.change_active_project))
        main_menu.update(Opt('get info about this device', device_info_menu.query))
        main_menu.update(Opt('upload all data from this device', ui_helpers.upload_all))

        return {'main_menu': main_menu, 'new_project_menu': new_project_menu, 'device_info_menu': device_info_menu,
                'project_info_menu': project_info_menu, 'demo_menu': demo_menu}


    def check_startup_conditions(self):
        if not ui_helpers.check_running_in_screen():
            print('this application must be run in a screen session. Please start a session with "screen -S master" and'
                  'and restart the application')
            sys.exit()

    def welcome(self):
        art = utils.import_ascii_art()
        utils.cprint(art['IOF'])
        utils.cprint(art['FISH_SEP'])

    def start_project(self):
        ui_helpers.pause_project()
        if not ui_helpers.active_project():
            print('cannot start a project that does not exist. Try selecting "create a new project" instead')
            return
        self.main_ctx = mptools.MainContext(metadata.MetaDataHandler(new_proj=False).simplify())
        self.main_ctx.Proc('RUN', runner.RunnerWorker, self.main_ctx)
        print(f'{self.main_ctx.metadata["proj_id"]} is now running in the background')
        if self.main_ctx.metadata['demo']:
            self.menus['demo_menu'].query()

    def change_active_project(self):
        change_project_menu = OptDict(prompt='select which project you want to activate')
        for proj in ui_helpers.existing_projects():
            change_project_menu.update(Opt(proj, ui_helpers.change_active_proj, proj))
        change_project_menu.query()

    def goodbye(self):
        if self.main_ctx:
            self.main_ctx.__exit__()
        utils.cprint('\ngoodbye')
        sys.exit()

if __name__ == '__main__':
    ui = UI()



