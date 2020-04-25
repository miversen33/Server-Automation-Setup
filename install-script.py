#!/usr/bin/env python3

import platform
import getpass
import os.path
import urllib
import shutil
import zipfile
import subprocess
import argparse

from getpass import getuser
from os.path import join
from urllib import request
from shutil import copyfileobj
from subprocess import run

TEMP_DIR = ''
GIT_URL = 'https://github.com/miversen33/Server-Automation-Setup/archive/master.zip'
PIP_URL = 'https://bootstrap.pypa.io/get-pip.py'
PIP_FILE = 'get-pip.py'
OUTPUT_ZIP = 'serverautomation.zip'
SAVE_DIR = 'Server-Automation-Setup-master'
INSTALL_DIR = ''
BIN_LOCATION = ''
INSTALL_COMMAND = 'python3 -m pip install .'

def _install_pip():
    print('Downloading Pip')
    with urllib.request.urlopen(PIP_URL) as response, open(join(TEMP_DIR, PIP_FILE), 'wb') as out_file:
        copyfileobj(response, out_file)
    print('Installing Pip')
    run(['python3', join(TEMP_DIR, PIP_FILE)])


def main():
    if platform.system() == 'Windows':
        TEMP_DIR = join("C:", "Users", getuser(), 'AppData', 'Local', "tmp")
        raise Exception('Windows install via manual install is not supported at this time')

    if platform.system() == 'Linux':
        TEMP_DIR = join("/tmp", "serverautomation")
        INSTALL_DIR = join("/home", getuser(), ".local", "lib", "serverautomation")
        BIN_LOCATION = join('/home', getuser(), '.local', 'bin')

    if platform.system() == 'Darwin':
        TEMP_DIR = join("/tmp", "serverautomation")

    if TEMP_DIR == '':
        raise Exception("Unable to establish OS type!")

    try:
        shutil.rmtree(TEMP_DIR)
    except FileNotFoundError:
        pass

    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass

    output = run(['python3', '-m', 'pip'], stdout=subprocess.DEVNULL)
    if output.returncode == 1 and 'No module named pip' in output.stdout:
        print('Unable to find pip')
        _install_pip()

    print('Downloading latest version from git')
    with urllib.request.urlopen(GIT_URL) as response, open(join(TEMP_DIR, OUTPUT_ZIP), 'wb') as out_file:
        copyfileobj(response, out_file)

    repo_zip = zipfile.ZipFile(join(TEMP_DIR, OUTPUT_ZIP), 'r')
    repo_zip.extractall(TEMP_DIR)
    repo_zip.close()

    os.chdir(join(TEMP_DIR, SAVE_DIR))
    os.rename('base-setup.py', 'setup.py')
    file = open('serverautomation/__init__.py', 'w')
    file.close()

    print('Installing Server Automation Tool')
    run(INSTALL_COMMAND.split(' '))

    print('Cleaing up')
    shutil.rmtree(TEMP_DIR)

    print("Finished! Execute 'serverautomation --help' to get started!")

if __name__ == '__main__':
    main()