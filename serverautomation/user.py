import getpass
import os.path
from getpass import getuser

class User:
    def __init__(self, username, password=None, user_shell=None, system_user=None, user_groups=None, ssh_key=None, home_directory=None, install_shell_if_missing=True):
        self.username = username
        self.password = password
        self.shell = user_shell if (user_shell is not None and not user_shell.isspace() and len(user_shell) > 0) else '"/usr/bin/bash"' 
        self.is_system_user = True if (system_user is not None and not system_user.isspace() and len(system_user) > 0 and system_user.lower() != 'false') else False
        self.groups = user_groups if (user_groups is not None and not user_groups.isspace() and len(user_groups) > 0) else []
        self.home_directory = home_directory if (home_directory is not None and not home_directory.isspace() and len(home_directory) > 0) else None
        self.install_shell_if_missing = install_shell_if_missing
        if isinstance(self.groups, str):
            self.groups = self.groups.split(',')

        self.ssh_key = ssh_key if (ssh_key is not None and not ssh_key.isspace() and len(ssh_key) > 0) else None
        
        if self.ssh_key:
            if 'default' == self.ssh_key.lower():
                current_user = getuser()
                # TODO Make this OS agnostic
                ssh_key = f'/home/{current_user}/.ssh/id_rsa.pub'
                if os.path.exists(ssh_key):
                    self.ssh_key = ssh_key
                else:
                    print(f'Unable to default ssh key for user: {current_user}')
                    self.ssh_key = None
            elif "/" not in self.ssh_key:
                current_user = getuser()
                ssh_key = f'/home/{current_user}/.ssh/{self.ssh_key}.pub'
                if os.path.exists(ssh_key):
                    self.ssh_key = ssh_key
                else:
                    print(f'Unable to ssh key {self.ssh_key}')
                    self.ssh_key = None
            if not self.ssh_key.endswith('.pub'):
                ssh_key += '.pub'