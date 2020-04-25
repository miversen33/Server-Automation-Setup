#!/usr/bin/env python3

import platform
import getpass
import os.path
import urllib
import shutil
import zipfile
import subprocess

from getpass import getuser
from os.path import join
from urllib import request
from shutil import copyfileobj
from subprocess import run

TEMP_DIR = ''
GIT_URL = 'https://github.com/miversen33/Server-Automation-Setup/archive/master.zip'
OUTPUT_FILE = 'serverautomation.zip'
SAVE_DIR = 'Server-Automation-Setup-master'
INSTALL_DIR = ''
INSTALL_COMMAND = 'ln -s $INSTALL_LOCATION$/__main__.py $BIN_LOCATION$/serverautomation'
PERMISSION_COMMAND = 'chmod +x $INSTALL_LOCATION$/__main__.py'

if platform.system() == 'Windows':
    TEMP_DIR = join("C:", "Users", getuser(), 'AppData', 'Local', "tmp")
    raise Exception('Windows install via manual install is not supported at this time!')

if platform.system() == 'Linux':
    TEMP_DIR = join("/tmp", "serverautomation")
    INSTALL_DIR = join("/home", getuser(), ".local", "lib", "serverautomation")
    BIN_LOCATION = join('/home', getuser(), '.local', 'bin')
    INSTALL_COMMAND = INSTALL_COMMAND.replace('$INSTALL_LOCATION$', INSTALL_DIR)
    INSTALL_COMMAND = INSTALL_COMMAND.replace('$BIN_LOCATION$', BIN_LOCATION) 
    PERMISSION_COMMAND = PERMISSION_COMMAND.replace('$INSTALL_LOCATION$', INSTALL_DIR)

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

print('Downloading latest version from git')
with urllib.request.urlopen(GIT_URL) as response, open(join(TEMP_DIR, OUTPUT_FILE), 'wb') as out_file:
    copyfileobj(response, out_file)

repo_zip = zipfile.ZipFile(join(TEMP_DIR, OUTPUT_FILE), 'r')
repo_zip.extractall(TEMP_DIR)
repo_zip.close()

os.chdir(join(TEMP_DIR, SAVE_DIR))
print('Putting files in place')
try:
    shutil.copytree(join(TEMP_DIR, SAVE_DIR, 'serverautomation'), INSTALL_DIR)
except FileExistsError:
    shutil.rmtree(INSTALL_DIR)
    shutil.copytree(join(TEMP_DIR, SAVE_DIR, 'serverautomation'), INSTALL_DIR)
run(INSTALL_COMMAND.split(' '))
run(PERMISSION_COMMAND.split(' '))

print('Cleaing up')
shutil.rmtree(TEMP_DIR)

print("Finished! Execute 'serverautomation --help' to get started!")