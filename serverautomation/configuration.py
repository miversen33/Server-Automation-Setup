import os
import os.path
import json
import sys
import getpass
import invoke
import crypt
import platform

try:
    import yaml
except ImportError:
    print('YAML Support Not Found. Unable to use YAML Configs')

from invoke import Responder
from getpass import getuser
from crypt import crypt

JSON = ['json',]
YAML = ['yaml' ,'yml']


class Configuration:
    VERBOSE = False
    class User:
        def __init__(self, username, password=None, user_shell=None, system_user=None, user_groups=None, ssh_key=None, home_directory=None, install_shell_if_missing=True):
            self.username = username
            self.password = password
            self.shell = user_shell if (user_shell is not None and not user_shell.isspace() and len(user_shell) > 0) else '"/usr/bin/bash"' 
            self.is_system_user = True if (system_user is not None and not system_user.isspace() and len(system_user) > 0 and system_user.lower() != 'false') else False
            self.groups = [group for group in user_groups if not group.isspace()] if user_groups is not None else []
            self.home_directory = home_directory if (home_directory is not None and not home_directory.isspace() and len(home_directory) > 0) else None
            self.install_shell_if_missing = install_shell_if_missing
            if isinstance(self.groups, str):
                self.groups = self.groups.split(',')

            self.ssh_key = ssh_key if (ssh_key is not None and not ssh_key.isspace() and len(ssh_key) > 0) else None
            
            if self.ssh_key:
                if 'default' == self.ssh_key.lower():
                    current_user = getuser()
                    if platform.system() == 'Windows':
                        ssh_key = os.path.join('C:\\', 'Users', current_user, '.ssh', 'id_rsa.pub')
                    else:
                        ssh_key = os.path.join('/home', current_user, '.ssh', 'id_rsa.pub')
                    if os.path.exists(ssh_key):
                        self.ssh_key = ssh_key
                    else:
                        print(f'Unable to default ssh key for user: {current_user}')
                        self.ssh_key = None
                elif "/" not in self.ssh_key and "\\" not in self.ssh_key:
                    current_user = getuser()
                    if platform.system() == 'Windows':
                        ssh_key = os.path.join('C:\\', 'Users', current_user, '.ssh', f'{self.ssh_key}.pub')
                    else:
                        ssh_key = os.path.join('/home', current_user, '.ssh', f'{self.ssh_key}.pub')

                    if os.path.exists(ssh_key):
                        self.ssh_key = ssh_key
                    else:
                        print(f'Unable to ssh key {self.ssh_key}')
                        self.ssh_key = None
                if not self.ssh_key.endswith('.pub'):
                    ssh_key += '.pub'
    class Config:
        STATUS_SUCCESS = 'success'
        STATUS_FAILURE = 'failure'
        STATUS_UNATTEMPTED = 'unattempted'
        STATUS_RUNNING = 'running'
    
        def __init__(self):
            super().__init__()
            self.status = self.STATUS_UNATTEMPTED

        def get_run_command(self, dal):
            raise NotImplementedError('Get Run Command Should Be Implemented By The Inheriting Class')

        def failed(self):
            self.status = self.STATUS_FAILURE

        def success(self):
            self.status = self.STATUS_SUCCESS
    
    class Configs:
        def __init__(self):
            super().__init__()
            self.__configs = []

        def add_config(self, config):
            self.__configs.append(config)

        def get_next_config(self):
            for config in self.__configs:
                if config.status == Configuration.Config.STATUS_UNATTEMPTED:
                    return config

        def is_finished(self):
            unattempted_scripts = [config for config in self.__configs if config.status == Configuration.Config.STATUS_UNATTEMPTED]
            return len(unattempted_scripts) == 0

    class UserConfig(Config):
        __GROUPS_PLACEHOLDER = '$GROUPS$'
        __SHELL_PLACEHOLDER = '$SHELL$'
        
        def __init__(self, user):
            super().__init__()
            self._user = user
            self.__parse_user_info()

        def get_run_command(self, dal):
            shell_path = dal.get_program_path(self._user.shell)
            self.user_add_command = self.user_add_command.replace(Configuration.UserConfig.__SHELL_PLACEHOLDER, shell_path)
            if self._user.groups:
                groups = dal.get_groups_on_server()
                # If you put the wrong admin group, we will attempt to fix it for you
                admin_groups = ['sudo', 'wheel', 'admin']
                missing_groups = []
                accepted_groups = []
                for group in self._user.groups:
                    if group not in groups:
                        print(f'Group {group} not found')
                        if group in admin_groups:
                            a_groups = [admin for admin in admin_groups if admin in groups]
                            if len(a_groups) > 0:
                                accepted_groups.append(a_groups[0])
                            else:
                                print(f'Unable to find replacement group for {group}')
                                missing_groups.append(group)
                        else:
                            missing_groups.append(group)
                    else:
                        accepted_groups.append(group)

                self.user_add_command = self.user_add_command.replace(self.__GROUPS_PLACEHOLDER, f'--groups {", ".join(str(group) for group in accepted_groups)} ')
                if missing_groups:
                    print(f'Unable to find the following groups for user {self._user.username} => {missing_groups}')
            
            return self.user_add_command

        def __parse_user_info(self):
            self.user_add_command = 'useradd '
            if self._user.is_system_user:
                self.user_add_command += f'--system --no-create-home '
            else:
                if self._user.home_directory:
                    self.user_add_command += f'--base-dir {self._user.home_directory} '
                else:
                    self.user_add_command += f'--create-home '
            self.user_add_command += f'--shell={Configuration.UserConfig.__SHELL_PLACEHOLDER} '
            self.user_add_command += Configuration.UserConfig.__GROUPS_PLACEHOLDER
            if self._user.password:
                self.user_add_command += '--password ' + crypt(self._user.password).replace("$",r"$") + ' '
            self.user_add_command += self._user.username

    class ConnectionConfig(Config):
        def __init__(self, input_args=None):
            super().__init__()
            self.ip_address = None
            self.hostname = None
            self.ssh_user = None
            self.ssh_user_password = None
            self.ssh_key = None
            self.ssh_key_password = None
            self.elevation_pass = None
            if input_args:
                self.__parse_input(input_args)
            else:
                raise Exception('No Input Provided')

        def get_run_command(self, dal):
            raise NotImplementedError('Connection Configuration Is Not Runnable')

        def __parse_input(self, input_args):
            if 'ip_address' in input_args.keys():
                self.ip_address = input_args['ip_address']
                self.hostname = self.ip_address
            if 'hostname' in input_args.keys() and self.ip_address is None:
                self.hostname = input_args['hostname']
                self.ip_address = self.hostname
            if 'ssh_user' in input_args.keys():
                self.ssh_user = input_args['ssh_user']
            if 'ssh_user_password' in input_args.keys():
                self.ssh_user_password = input_args['ssh_user_password']
            if 'ssh_key_password' in input_args.keys():
                self.ssh_key_pass = input_args['ssh_key_password']
            if 'elevation_password' in input_args.keys():
                self.elevation_pass = input_args['elevation_password']
            if 'ssh_key' in input_args.keys() or not self.ssh_user:
                self.__parse_ssh_key(input_args['ssh_key'] if 'ssh_key' in input_args.keys() else None)

        def __parse_ssh_key(self, ssh_key):
            if ssh_key is None:
                current_user = getuser()
                if platform.system() == 'Windows':
                    ssh_key = os.path.join('C:\\', 'Users', current_user, '.ssh', 'id_rsa')
                else:
                    check_ssh_key = os.path.join('/home', current_user, '.ssh', 'id_rsa')
                if os.path.exists(check_ssh_key):
                    ssh_key = check_ssh_key
                    if Configuration.VERBOSE:
                        print(f"No ssh key provided. Utilizing {current_user}'s key at {check_ssh_key}")
                else:
                    ssh_key = None
                    if Configuration.VERBOSE:
                        print('Unable to find ssh key. We will prompt for password')
            self.ssh_key = ssh_key

    class ScriptConfig(Config):
        PARAMS = [
            'runas',
            'local'
        ]

        class Param:
            def __init__(self, param):
                self.str_param = param
                self.name = param.split('-')[-1].split('=')[0].lower()
                try:
                    self.value = self.str_param.split('=')[1]
                except IndexError:
                    self.value = True

        def __init__(self, script):
            super().__init__()
            split_script = script.split(' ')
            self.script = split_script[0]
            if len(split_script) > 1:
                params = [self.Param(param) for param in split_script if param != self.script and len(param) > 0 and not param.isspace()]
                self.check_params(params)

        def check_params(self, params):
            self.params = [param for param in params if param.name not in self.PARAMS]
            for param in params:
                self.__setattr__(param.name, param.value)

        def get_params(self):
            param_string = ""
            for param in self.params:
                if param in self.PARAMS:
                    continue
                param_string += f' {param.str_param} '
            return param_string

        def get_run_command(self, dal):
            command = ''
            params = self.get_params()
            if dal._connection:
                params += f' --host={dal._connection.host}'
                params += f' --user={dal._connection.user}'
                try:
                    if dal._connection.connect_kwargs["password"]:
                        params += f' --password={dal._connection.connect_kwargs["password"]}'
                except:
                    pass
                try:
                    if dal._connection.connect_kwargs["key_filename"]:
                        params += f' --ssh_key={dal._connection.connect_kwargs["key_filename"]}'
                except:
                    pass
                try:
                    if dal._connection.connect_kwargs["passphrase"]:
                        params += f' --ssh_passphrase={dal._connection.connect_kwargs["passphrase"]}'
                except:
                    pass
            if self.runas:
                path = os.path.normpath(self.script)
                command = f'su {self.runas} "$PATH$/{path.split(os.sep)[-1]} {params}" -c -s /bin/sh'
            else:
                command = f'{self.script} {params}'
            return command

        def __getattr__(self, attr):
            if attr.startswith('__') and attr.endswith('__') and attr not in self.__dict__.keys():
                raise AttributeError
            if attr not in self.__dict__.keys():
                return None
            else:
                return super().__getattr__(attr)

    class OptionalConfig(Config):
        def __init__(self, command, param):
            super().__init__()
            self.__command = command
            self.__param = param

        def get_run_command(self, dal):
            try:
                return dal.custom_command(self.__command, self.__param)
            except NotImplementedError as exception:
                # TODO Implement logging
                return ''

    class DependencyConfig(Config):
        def __init__(self, dependency):
            super().__init__()
            self.__dependency = dependency

        def get_run_command(self, dal):
            return dal.install(self.__dependency)

    class ServerConfig(Config):
        def __init__(self):
            super().__init__()
            self.__dependency_configs = Configuration.Configs()
            self.__dependency_configs.add_config(Configuration.DependencyConfig('python3'))
            self.__user_configs = Configuration.Configs()
            self.__optional_configs = Configuration.Configs()
            self.__external_scripts = Configuration.Configs()
            self.__update_server = None
            self.__reboot_server = None
            self.__upgrade_server = None
            self.__failed_commands = []
            self.__current_command_string_form = ''
            self.last_command = None
            self.current_command = None

        def add_new_user(self, new_user):
            self.__user_configs.add_config(Configuration.UserConfig(new_user))

        def add_dependency(self, dependency):
            # Excluding this as we are already using it
            if dependency != 'python3':
                self.__dependency_configs.add_config(Configuration.DependencyConfig(dependency))

        def add_optional_configuration(self, additional_configuration_command, additional_configuration_param):
            if isinstance(additional_configuration_param, list):
                [self.add_optional_configuration(additional_configuration_command, param) for param in additional_configuration_param]
            optional_config = Configuration.OptionalConfig(additional_configuration_command, additional_configuration_param)
            if additional_configuration_command.lower() == 'update':
                self.__update_server = optional_config 
                return
            if additional_configuration_command.lower() == 'upgrade':
                self.__upgrade_server = optional_config
                return
            if additional_configuration_command.lower() == 'reboot_on_finish' or additional_configuration_command.lower() == 'reboot':
                self.__reboot_server = Configuration.OptionalConfig('reboot', additional_configuration_param)
                return
            self.__optional_configs.add_config(optional_config)

        def add_external_script(self, external_script):
            self.__external_scripts.add_config(Configuration.ScriptConfig(external_script))

        def get_next_command_info(self, dal):
            self.status = self.STATUS_RUNNING
            config = ''
            location = 'remote'
            extra_params = None
            extra_info = None
            if self.__update_server and self.__update_server.status == Configuration.Config.STATUS_UNATTEMPTED:
                config = self.__update_server

            if self.__upgrade_server and self.__upgrade_server.status == Configuration.Config.STATUS_UNATTEMPTED:
                config = self.__upgrade_server

            if not config and not self.__dependency_configs.is_finished():
                config = self.__dependency_configs.get_next_config()

            if not config and not self.__user_configs.is_finished():
                config = self.__user_configs.get_next_config()
                if config._user.ssh_key:
                    extra_params = 'copy_ssh_key'
                extra_info = config._user

            if not config and not self.__optional_configs.is_finished():
                config = self.__optional_configs.get_next_config()

            if not config and not self.__external_scripts.is_finished():
                config = self.__external_scripts.get_next_config()
                location = 'local' if config.local else 'remote'
                extra_params = None
                if location == 'remote':
                    extra_params = 'copy'
                    extra_info = config.script

            if not config and self.__reboot_server and self.__reboot_server.status == Configuration.Config.STATUS_UNATTEMPTED:
                config = self.__reboot_server

            self.last_command = self.__current_command_string_form
            self.current_command = config
            if self.current_command != '':
                self.__current_command_string_form = self.current_command.get_run_command(dal)
                return Configuration.ReturnInfo(
                    command      = self.__current_command_string_form,
                    location     = location,
                    extra_params = extra_params,
                    extra_info   = extra_info
                )
            else:
                if len(self.__failed_commands) > 0:
                    self.status = self.STATUS_FAILURE
                else:
                    self.status = self.STATUS_SUCCESS
                return None

        def current_command_failed(self):
            self.current_command.failed()
            self.__failed_commands.append(self.current_command)
            print(f'Command Failed: {self.__current_command_string_form}')

        def current_command_success(self):
            self.current_command.success()

        def reset_failed_commands(self):
            for command in self.__failed_commands:
                command.status = self.STATUS_UNATTEMPTED

    class ReturnInfo:
        def __init__(self, command, location, extra_params=None, extra_info=None):
            self.command = command
            self.location = location
            self.extra_params=extra_params
            self.extra_info=extra_info

    def __init__(self, input_file, verbose=False):
        self.connection_config = None
        self.server_config = Configuration.ServerConfig()
        Configuration.VERBOSE = verbose
        self.__parse_input(input_file)

    def connection(self):
        return self.connection_config

    def configs(self):
        return self.server_config

    def reset_failures(self):
        self.server_config.reset_failed_commands()

    def __parse_input(self, input_file):
        if not os.path.exists(input_file):
            print(f'Unable to open input config {input_file}. Cannot locate file')
            sys.exit(1)

        connection_setup = None
        extension = input_file.split('.')[-1]
        if extension in JSON:
            with open(input_file) as json_data:
                connection_setup = json.load(json_data)
        if extension in YAML:
            with open(input_file) as yaml_data:
                connection_setup = yaml.safe_load(yaml_data)

        if not connection_setup:
            raise Exception(f'Unable to load configuration file {input_file}')

        if 'server_connection' in connection_setup.keys():
            self.connection_config = Configuration.ConnectionConfig(connection_setup['server_connection'])
        else:
            self.connection_config = Configuration.ConnectionConfig()

        if not self.connection_config.ip_address:
            raise Exception('No IP Address/Hostname provided!')
        if 'users' in connection_setup.keys():
            shell_dependencies = self.__create_users(connection_setup['users'])

        if 'dependencies' in connection_setup.keys():
            [self.server_config.add_dependency(shell_dependency) for shell_dependency in shell_dependencies]
            [self.server_config.add_dependency(dependency) for dependency in connection_setup['dependencies']]

        if 'server_configuration' in connection_setup.keys() or 'server_config' in connection_setup.keys():
            try:
                c = connection_setup['server_configuration']
            except:
                c = connection_setup['server_config']
            if 'enable_service' in c.keys():
                [self.server_config.add_optional_configuration('enable_service', service) for service in c['enable_service']]
            [self.server_config.add_optional_configuration(command, param) for command, param in c.items() if command != 'enable_service']
        if 'configurations' in connection_setup.keys():
            [self.server_config.add_external_script(script) for script in connection_setup['configurations']]

    def __create_users(self, users):
        shells = set()
        for u in users:
            username = u['username']
            password = u['password'] if 'password' in u.keys() else None
            shell = u['shell'] if 'shell' in u.keys() else None
            groups = u['groups'] if 'groups' in u.keys() else None
            system_user = u['system_user'] if 'system_user' in u.keys() else None
            ssh_key = u['ssh_key'] if 'ssh_key' in u.keys() and not system_user else None
            home_directory = u['home_directory'] if 'home_directory' in u.keys() and not system_user else None
            install_shell_if_missing = True if not system_user else False
            if (
                    'install_shell_if_missing' in u.keys() and 
                    not system_user and 
                    u['install_shell_if_missing'].lower() != 'false' and 
                    u['install_shell_if_missing'] != '' and 
                    u['install_shell_if_missing'].isspace()
                ):
                install_shell_if_missing = True
            user_info = Configuration.User(
                    username=username,
                    password=password,
                    user_shell = shell,
                    system_user = system_user,
                    user_groups = groups,
                    ssh_key = ssh_key,
                    home_directory = home_directory,
                    install_shell_if_missing = install_shell_if_missing,
                )
            if install_shell_if_missing and shell:
                shells.add(shell)
            self.server_config.add_new_user(user_info)
        return shells