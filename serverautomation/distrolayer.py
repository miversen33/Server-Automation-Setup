import subprocess
import sys
import invoke

from subprocess import run as Run
from invoke.exceptions import UnexpectedExit

class DistroAbstractionLayer:
    _knowndistros = ['ubuntu', 'debian', 'manjaro', 'arch', 'centos', 'raspbian', 'red hat', 'fedora']
    # Maps the known distributions to parent distributions so we dont need to handle
    # lots of package managers
    distro_map = {
        'ubuntu' : 'debian',
        'debian' : 'debian',
        'raspbian' : 'debian',
        'manjaro': 'arch',
        'arch': 'arch',
        'centos': 'red hat',
        'red hat': 'red hat',
        'fedora': 'red hat'
    }

    # Map to fix redhat being dumb
    _redhat_dumb_map = {
        'red' : 'red hat'
    }

    # Map of common commands, by distro
    _command_map = {
        'debian': {
            "install": "apt-get install $INSTALL$ -y",
            "upgrade": "apt-get upgrade -y",
            "update": "apt-get update -y",
            "hostname": "hostnamectl set-hostname $HOSTNAME$",
            "reboot": "reboot",
            "enable_service": "systemctl enable $ENABLE_SERVICE$",
        },

        'arch': {
            "install": "pacman -Sy $INSTALL$ --noconfirm",
            "update": "pacman -Syy",
            "upgrade": None,
            "hostname": "hostnamectl set-hostname $HOSTNAME$",
            "reboot": "reboot",
            "enable_service": "systemctl enable $ENABLE_SERVICE$",
        },

        'red hat': {
            "install": "yum install $INSTALL$ -y",
            "update": "yum update -y",
            "upgrade": None,
            "hostname": "hostnamectl set-hostname $HOSTNAME$",
            "reboot": "reboot",
            "enable_service": "systemctl enable $ENABLE_SERVICE$",
        }
    }

    distro_map_commands = {
        'lsb_release -ds': lambda command_output: command_output.rstrip().split(' ')[0],
        'cat /etc/redhat-release': lambda command_output: command_output.rstrip().split(' ')[0],
        'cat /etc/issue': lambda command_output: command_output.rstrip().split(' ')[0]
    }

    _custom_commands = {}

    def __init__(self, remote_connection=None, custom_command_map=None):
        """
            we expect if you pass a remote_connection, it is an already connected paramiko connection.
            custom_command_map needs to be a dictionary with the key being the command, and the value being a string
            command to run. if the command takes an input, it the input param needs to be formatted with the command name (upper case only), surrounded by $$. For example,
            If your command was "install", your dictionary should look as follows.

            dict(install="some command $INSTALL$).

            Currently, we only allow for single param custom commands. If you need more, you will have to build it yourself.
        """
        self._connection = remote_connection
        self.distro = self.__get_distro__()
        if custom_command_map:
            self._custom_commands = dict(custom_command_map)

    def __get_distro__(self):
        command = None
        if self._connection:
            command = lambda command_input: self._connection.run(command_input, hide=True).stdout
        else:
            command = lambda command_input: Run(command_input.split(' '), stdout=subprocess.PIPE).stdout.decode('utf-8')
        success = False
        distro = None
        for key, function in self.distro_map_commands.items():
            if success:
                break
            try:
                distro = function(command(key))
                if distro.lower() in self._redhat_dumb_map.keys():
                    distro = self._redhat_dumb_map[distro.lower()]
                if distro:
                    success = True
            except FileNotFoundError:
                success = False
            except UnexpectedExit:
                success = False

        if not distro:
            raise Exception('Unknown Distribution Of Linux')
        if distro.lower() not in self._knowndistros:
            print(f"We aren't exactly sure how to handle {distro}. We will try out best")
        return distro

    def install(self, package):
        return self._create_command('install', param=package)

    def update(self):
        return self._create_command('update')

    def upgrade(self):
        return self._create_command('upgrade')
    
    def set_hostname(self, hostname):
        return self._create_command('hostname', param=hostname)

    def reboot(self):
        return self._create_command('reboot')

    def custom_command(self, command, param=None):
        return self._create_command(command, param)

    def get_groups_on_server(self):
        command = 'cat /etc/group'
        output = None
        if self._connection:
            output = self._connection.run(command, hide=True).stdout
        else:
            output = Run(command.split(' '), stdout=subprocess.PIPE).stdout.decode('utf-8')
        return [group.split(':')[0] for group in output.split('\n')]

    def get_program_path(self, program):
        input_command = f'which {program}'
        if self._connection:
            command = lambda input_command: self._connection.run(input_command, hide=True).stdout
        else:
            command = lambda input_command: Run(input_command.split(' '), stdout=subprocess.PIPE).stdout.decode('utf-8')
        try:
            output = command(input_command)
            if output.startswith('which:'):
                output = ''
            else:
                output = output.rstrip()
        except UnexpectedExit as exception:
            result = exception.result
            if result.return_code == 1:
                output = result.stdout
        return output if output != '' else None

    def _create_command(self, command, param=None):
        d_map = self.distro_map[self.distro.lower()]
        if command not in self._custom_commands.keys() and command not in self._command_map[d_map].keys():
            raise NotImplementedError(f'{command} is not implemented for {self.distro}')
        _c = None
        if command in self._custom_commands.keys():
            _c = self._command_map[command]
        if not _c and command in self._command_map[d_map].keys():
            _c = self._command_map[d_map][command]
        if param:
            _c = _c.replace(f"${command.upper()}$", param)
        return _c