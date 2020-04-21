#!/usr/bin/env python

_available_formats = 'JSON'

import serverautomation
import argparse
import json
import os
import os.path
import socket
import sys
import getpass
import random
import subprocess
import pickle
import datetime

try:
    import yaml
    _available_formats += ', YAML'
except ImportError:
    print("YAML support not found. To install YAML, execute 'python3 -m pip install pyyaml'")

try:
    import fabric
    from fabric import Connection
except ImportError as exception:
    print("Fabric not installed. Please re-run setup script. 'Execute setupscript.py'")
    raise exception

try:
    import paramiko
    from paramiko import ssh_exception
except ImportError as exception:
    print("Paramiko not installed. Please re-run setup script. 'Execute setupscript.py'")
    raise exception

try:
    import invoke
    import invoke.exceptions as invoke_exceptions
    from invoke import Responder
except ImportError as exception:
    print("Invoke not installed. Please re-run setup script. 'Execute setupscript.py'")
    raise exception

from serverautomation.configuration import Configuration 
from serverautomation.distrolayer import DistroAbstractionLayer
from getpass import getpass, getuser
from random import randint
from os.path import isfile, join

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help=f"A Configured Input File (Required). Available Formats are: {_available_formats}")
parser.add_argument("-v", "--verbose", help="LOG ALL THE THINGS", action='store_true')
parser.add_argument("-e", "--onfail", help="How to handle failure. Options are (continue:default, die)")
parser.add_argument('-d', '--debug', help="When enabled, instead of executing commands on remote server, we simply print them to console.", action='store_true')

SUDOPASS_LAMBDA = lambda elevation_password: Responder(
    pattern=r'\[sudo\] password:',
    response=f'{elevation_password}\n'
)

DEBUG = False
TMP_PATH = f'/tmp/{randint(0, 10000)}'
CACHE_DIR = f'/home/{getuser()}/.server_automation/'
try:
    os.mkdir(CACHE_DIR)
except FileExistsError:
    pass
VERBOSE = False

def connect_to_server(config, retry_limit=4, current_retry_count=0):
    hostname = config.hostname
    elevation_password = config.elevation_pass
    ssh_key_password = config.ssh_key_password
    user = config.ssh_user
    password = config.ssh_user_password
    try:
        # We should be creating the connect_kwargs before hand and adding the key if it was provided
        server_connection = Connection(host=hostname, user=user, connect_kwargs=dict(password=password, passphrase=ssh_key_password))
        # Yes, we are saving the elevation password to an object and passing it around. Fight me
        server_connection.sudopass = elevation_password
        # Checking to make sure we can actually get connected to the server.
        if current_retry_count == 0:
            print(f'Attempting to connect to {hostname}')
        else:
            print(f'Attempting to connect to {hostname}. Attempt #{current_retry_count}')
        server_connection.run('cat /dev/null')
        # Checking to make sure we have sudo privileges on the server
        print(f'Obtaining sudo privileges')
        server_connection.sudo('cat /dev/null', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
        print(f'Establishing OS Type')
        server_connection.distro = DistroAbstractionLayer(server_connection)

        return server_connection
    except socket.gaierror:
        print(f'Unable to reach host "{hostname}"')
        sys.exit(1)
    except ssh_exception.PasswordRequiredException:
        if current_retry_count >= retry_limit:
            print(f'Failed to connect to host "{hostname}" due to some issue with ssh key password')
            sys.exit(1)

        config.ssh_key_pass = getpass('Please Enter SSH Password: ')
        return connect_to_server(
            config,
            current_retry_count=current_retry_count+1
        )
    except ssh_exception.SSHException:
        if current_retry_count >= retry_limit:
            print(f'Failed to connect to host "{hostname}" due to incorrect ssh key password"')
            sys.exit(1)
        
        print('Invalid SSH Key password')
        config.ssh_key_pass = None
        return connect_to_server(
            config,
            current_retry_count=current_retry_count+1
        )
    except invoke_exceptions.AuthFailure:
        if current_retry_count >= retry_limit:
            print(f'Failed to obtain administrator permissions on "{hostname}" due to bad sudo password')
            sys.exit(1)

        config.elevation_pass = getpass('Incorrect sudo password. Please re-enter sudo password: ')
        return connect_to_server(
            config,
            current_retry_count=current_retry_count+1
        )

def run_remotely(server_connection, command, extra_params, extra_info):
    successful = False
    if extra_params and extra_params == 'copy':
        if not DEBUG:
            try:
                server_connection.sudo(f'''mkdir -p {TMP_PATH}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chown {server_connection.user}:{server_connection.user} {TMP_PATH}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.put(extra_info, TMP_PATH)
                
                server_connection.sudo(f'''{command.replace('$PATH$', TMP_PATH)}''', watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                successful = True
            except Exception as exception:
                print(exception)
                if 'already' in exception:
                    successful = True
        else:
            print(f'''mkdir -p {TMP_PATH}''')
            print(f'Copying {extra_info} to {TMP_PATH}')
            print(f'''{command.replace('$PATH$', TMP_PATH)}''')
            successful = True
    else:
        if not DEBUG:
            try:
                if 'reboot' in command:
                    server_connection.sudo(f'''rm -rf {TMP_PATH}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''{command}''', watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)], hide=not VERBOSE)
                successful = True
            except Exception as exception:
                print(exception)
                if 'already' in exception.result.stderr:
                    successful = True
        else:
            if 'reboot' in command:
                print(f'''rm -rf {TMP_PATH}''')
            print(f'''{command}''')
            successful = True
    if extra_params == 'copy_ssh_key':
        try:
            user = extra_info
            if VERBOSE:
                print(f'Copying ssh key over to {user.username}')
            tmp_path = f'{TMP_PATH}/{user.username}/'
            output = server_connection.sudo(f'''python3 -c "from os.path import expanduser; print(expanduser('~{user.username}'))"''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
            final_path = f'{output.stdout.rstrip()}/.ssh'
            path = os.path.normpath(user.ssh_key)
            ssh_key = path.split(os.sep)[-1]

            if not DEBUG:
                server_connection.sudo(f'''mkdir -p {tmp_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chown {server_connection.user}:{server_connection.user} {tmp_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''mkdir -p {final_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.put(user.ssh_key, tmp_path)
                server_connection.sudo(f'''cp {tmp_path}{ssh_key} {final_path}/authorized_keys''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chmod 700 {final_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chmod 600 {final_path}/authorized_keys''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chown {user.username}:{user.username} {final_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''chown {user.username}:{user.username} -R {final_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
                server_connection.sudo(f'''rm -rf {tmp_path}''', hide=not VERBOSE, watchers=[SUDOPASS_LAMBDA(server_connection.sudopass)])
            else:
                print(f'''mkdir -p {tmp_path}''')
                print(f'''chown {server_connection.user}:{server_connection.user} {tmp_path}''')
                print(f'''mkdir -p {final_path}''')
                print(f'''Copying {user.ssh_key} over to server''')
                print(f'''cp {tmp_path}{ssh_key} {final_path}/authorized_keys''')
                print(f'''chmod 700 {final_path}''')
                print(f'''chmod 600 {final_path}/authorized_keys''')
                print(f'''chown {user.username}:{user.username} {final_path}''')
                print(f'''chown {user.username}:{user.username} -R {final_path}''')
                print(f'''rm -rf {tmp_path}''')
            successful = True
        except invoke_exceptions.UnexpectedExit as exception:
            print(f'Unable to copy {user.ssh_key} over to {user.username}')
            print(exception)
            if 'already' in exception.result.stderr:
                successful = True
    return successful

def run_locally(server_connection, command, extra_params, extra_info):
    successful = False
    if not DEBUG:
        try:
            child = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE, shell=True)
            child.communicate(input=server_connection.sudopass),
            wait_limit = 10000
            wait = 0
            while wait < wait_limit and child.wait() != 0:
                wait += 1
            
            if wait >= wait_limit:
                print(f'Something happened and we were unable to process {command}')
                print(child.stdout)
                successful = False
            else:
                successful = True
        except Exception as exception:
            print(exception)
            successful = False
            if 'already' in exception.stderr.decode('utf-8'):
                successful = True
    else:
        print(f'''{command}''')
        successful = True
    return successful

def parse_file(input_file):
    if not input_file:
        raise FileNotFoundError('Input File Not Provided')
    files_in_cache = [file for file in os.listdir(CACHE_DIR) if isfile(join(CACHE_DIR, file))]
    for file in files_in_cache:
        if input_file in file:
            return join(CACHE_DIR, file), True
    if not os.path.exists(input_file):
        raise FileNotFoundError(f'Input File: {input_file} Not Found')
    return input_file, False

input_args = parser.parse_args()
DEBUG = input_args.debug
file, resume = parse_file(input_args.file)
VERBOSE = input_args.verbose
if input_args.onfail == 'die':
    die_on_fail = True
else:
    die_on_fail = False

if resume:
    with open(file, 'rb') as resume_data:
        server_setup = pickle.load(resume_data)
        server_setup.reset_failures()
    os.remove(file)
else:
    server_setup = Configuration(file, VERBOSE)
connection_info = server_setup.connection()
server_configs = server_setup.configs()
server_connection = connect_to_server(connection_info)
dal = server_connection.distro
print(f'Distro: {dal.distro}')
running = True
while running:
    info = server_configs.get_next_command_info(dal)
    if info:

        if info.location == 'remote':
            success = run_remotely(server_connection, info.command, info.extra_params, info.extra_info)
        else:
            success = run_locally(server_connection, info.command, info.extra_params, info.extra_info)
        if success:
            server_configs.current_command_success()
        else:
            server_configs.current_command_failed()
            if die_on_fail:
                break
        running = True
    else:
        running = False

if server_configs.status == Configuration.Config.STATUS_FAILURE:
    output_file_name = f'{connection_info.ip_address}-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}'
    output_file = open(f'{CACHE_DIR}.{output_file_name}.sacfg', 'wb')
    pickle.dump(server_setup, output_file)
    output_file.close()
    if die_on_fail:
        print(f'Server Setup Failed. To pickup where we left off, execute the following command. python3 -m server_setup --file {output_file_name}')
    else:
        print(f'Server Setup completed with errors. To rerun failed scripts, execute the following command. python3 -m server_setup --file {output_file_name}')
else:
    print('Server Setup complete!')