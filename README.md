# Server Automation Setup

A helper program that will setup a remote server for you

## Table Of Contents
- [Installation](#installation)
  - [PIP](#pip)
  - [Manual](#manual)
  - [Dependencies](#dependencies)
  - [Uninstallation](#uninstallation)
- [How To Run](#how-to-run)
  - [Available parameters](#available-parameters)
  - [What About Server Failure?](#what-about-server-failure)
- [Configuration](#configuration)
  - [JSON](#json)
- [YAML](#yaml)

***
<br>

## Installation
### PIP
[Server Automation Setup](https://pypi.org/project/server-automation-setup/) can be installed from pip via 
```
python3 -m pip install server-automation-setup
```
<br>

### Manual
Or if you are feeling adventurous, you can download the install script from github and run the following command.
```
curl https://raw.githubusercontent.com/miversen33/Server-Automation-Setup/master/install-script.py >> /tmp/install-script.py && python3 /tmp/install-script.py
```
[**NOTE: Be careful executing random files off the internet. Always inspect them first**](https://github.com/miversen33/Server-Automation-Setup/blob/master/install-script.py)

Once its finished, you should see output that looks like 
```
Finished! Execute 'serverautomation --help' to get started!
```
<br>

### Dependencies
Regardless of which decision you chose for installation, our dependencies are already installed. 
The programs we rely on to function properly are
* [YAML](https://github.com/yaml/pyyaml)
* [Fabric](https://github.com/fabric/fabric)
* [Invoke](https://github.com/pyinvoke/invoke)
* [Paramiko](https://github.com/paramiko/paramiko)

<br>

### Uninstallation
If you installed the server automation tool via pip, you can uninstall it with the following command 
```
python3 -m pip uninstall server-automation-setup
```

If you installed te server automation tool manually, pip may not recognize it. To perform an uninstall in this case, run the following command
```
curl https://raw.githubusercontent.com/miversen33/Server-Automation-Setup/master/install-script.py >> /tmp/install-script.py && python3 /tmp/install-script.py --uninstall
```
[**NOTE: Be careful executing random files off the internet. Always inspect them first**](https://github.com/miversen33/Server-Automation-Setup/blob/master/install-script.py)

***
<br>

## How To Run
Running the setup script is easy. Simply provide it a configuration file to load and it handles everything else.
```
serverautomation -f=yourfile
```
### Available parameters
```
-f, --file: Your configuration File.
    This must be a JSON or YAML file, unless the script excplicitly gives you a file to run.
-v, --verbose: Tells the system to print out more details
-d, --debug: When enabled, we will still connect to the remote server, 
    but then we simply dump all the commands we would run to the terminal window for the user to see
-e, --onfail: How to handle failure. Options are (continue:default, die)
```

### What About Server Failure?
It happens. Something causes one of the installation scripts to crash. The server is bounced. One of the external scripts breaks. Etc.
So what happens when a failure occurs while setting up your shiny new server? When an error occurs, we handle it (depending on what [`--onfail`](#available-parameters) is set to). Regardless of the status of [`--onfail`](#available-parameters), we will keep track of the script(s) that fail during setup. Once we are finished running, if failures were found, we provide you a special file that you can use to only execute the failed script(s). It will look something like this
```
Server Setup completed with errors. To rerun failed scripts, execute the following command. serverautomation --file 127.0.0.1-20200420-202251
```

***
<br>

## Configuration
Configuration files can be provided in either [JSON](#json) or [YAML](#yaml) formats. Below are those 2 formats, with documentation of any available options that can be provided

### [JSON](https://github.com/miversen33/Server-Automation-Setup/blob/master/setupconfig.doc.json)
```
{
    "server_connection": {
        // Optional
        // This needs to be an ip address that is accessible from the box this is ran off of
        "ip_address": "127.0.0.1",
        // Optional
        // Either provide this or ip address. If you provide both, we will use the ip address. 
        "hostname": "some-host",
        // Optional
        // if not provided, we assume you want to ssh in as root.
        "ssh_user": "someuser",
        // Optional
        // if used, this needs to be the path to an ssh key, or if the file is in the same directory this can be the ssh key name directly
        "ssh_key": "id_rsa",
        // Optional
        // If not provided, we will ask for it once
        "ssh_key_password": "somepassword",
        // Optional
        // The sudo password for the server. If not provided, we will ask for it
        "elevation_password": "somepassword"
    },
    "users": [
        {
            "username": "testuser",
            // This can be 
            // - An empty string or 'None' (both equate to None)
            // - Cleartext password
            // In all cases the password must be cleartext (you're using a config script to setup users. Deal with the security risk, or dont use it)
            "password": "",
            // The rest of these are optionals
            
            // Can either be full path or program name.
            "shell": "zsh",
            // Optional
            // The expected home directory location
            // If not provided (and not a system_user), we will simply let linux decide where to put you.
            // Usually by default this will be /home/username
            "home_directory": "/home/",
            // List of groups. If you only want it to be in its own group, leave this blank
            // The system will attempt to make sure that the user has sudo permissions if it is placed in
            // either sudo or wheel. The system will try to verify that either of those groups exist and have the appropriate permission
            // It is better to be sure you know what you want here, but we will try for you
            "groups": "sudo",
            // Optional
            // This is not case sensitive, but it does have to be a boolean T/F. If left blank, it will be considered false
            "system_user": "False",
            // Optional
            // If provided, we will copy an ssh key over to the server for you. If you want to just use the 
            // key provided, simply supply 'default' (not case sensitive). Otherwise, we will expect 
            // the name of the key you are looking for. If you do not provide a full path to it, we will 
            // check in the running user's .ssh directory, however that isn't the best idea. You should
            // really just provide a full path
            // NOTE! If the user is a system_user (ie, no login), this will be ignored
            "ssh_key": "default"
        }
    ],
    "dependencies": [
        // Optional
        // Experimental
        // We will attempt to install the dependencies in this list regardless of the distro of the box
        // we are on
        "someprogram1","someprogram2","someprogram3"
    ],
    // EXPIRAMENTAL!
    // Optional
    "server_configuration": {
        // Sets the hostname of the server to the provided hostname
        "hostname": "newhostname_for_server",
        // Tells the system to update the server. Not case sensitive. If present, this will be run before anything else
        "update": "True",
        // Tells the system to upgrade the server distro. Not case sensitive
        "upgrade": "True",
        // Tells the system to disconnect and restart the server on completion. This is the very last thing ran, if present
        "reboot_on_finish": "True",
        // Services that we need to enable for the server. We expect the service(s) to be installed already. If its not, you're on
        // your own. Don't set us up for failure. 
        "enabled_service": [
            "someprogram1",
            "someprogam2"
        ]
    },
    "configurations":[
        // Optional
        // A list of scripts to execute in order on the server box.
        // Make sure that the server has the software installed to execute the script language though
        // 
        // You can additionally provide params for the system to obey when executing the script provided. You can also provide 
        // params to the script itself. We will consume the params we expect and pass all the rest to the script
        // The following params are reserved for us (meaning, if they are provided, we will consume then and they will not be passed along). None of these are case sensitive
        // --runAs=whatever user you want the script to be run as
        // --local tells us that you want the script to be locally (on the hosting box) instead of remotely. Note, we assume by default the scripts are to be
        //         run remotely. 
        //
        // You can also provide params for your script here, and those are passed to your script as well
        //
        // We pass the following additional params to every script that is run locally
        // --host=whatever the server ip is that we just finished our setup on
        // --user=whatever the user is that we used when initiating our connection to the server
        // --password=whatever the user's password is.
        // --ssh_key=whatever the ssh key is that was used to connect to the server. Note this is only provided if we were provided one
        // --ssh_passphrase=whatever the passphrase is for the key. Note this is only provided if we are provided it
        "someFile1.py --runAs=root",
        "someFile2.pl --someparam=somevalue",
        "someFile3.sh"
    ]

}
```

### [YAML](https://github.com/miversen33/Server-Automation-Setup/blob/master/setupconfig.doc.yaml)
```yaml
server_connection:
  # Optional
  # This needs to be an ip address that is accessible from the box this is ran off of
  ip_address: 127.0.0.1
  # Optional
  # Either provide this or ip address. If you provide both, we will use the ip address.
  hostname: some-host
  # Optional
  # if not provided, we assume you want to ssh in as root.
  ssh_user: someuser
  # Optional
  # if used, this needs to be the path to an ssh key, or if the file is in the same directory this can be the ssh key name directly
  ssh_key: id_rsa
  # Optional
  # If not provided, we will ask for it once
  ssh_key_password: somepassword
  # Optional
  # The sudo password for the server. If not provided, we will ask for it
  elevation_password: somepassword
users:
- username: testuser
  # This can be 
  # - An empty string or 'None' (both equate to None)
  # - Cleartext password
  password: ''
  # The rest of these are optionals

  # Can either be full path or program name.
  shell: zsh
  # Optional
  # The expected home directory location
  # If not provided (and not a system_user), we will simply let linux decide where to put you.
  # Usually by default this will be /home/username
  home_directory: "/home/"
  # List of groups. If you only want it to be in its own group, leave this blank
  # The system will attempt to make sure that the user has sudo permissions if it is placed in
  # either sudo or wheel. The system will try to verify that either of those groups exist and have the appropriate permission
  # It is better to be sure you know what you want here, but we will try for you
  groups: 
    - sudo
    - someothergroup1
    - someothergroup1
  # Optional
  # This is not case sensitive, but it does have to be a boolean T/F. If left blank, it will be considered False
  system_user: 'False'
  # Optional
  # If provided, we will copy an ssh key over to the server for you. If you want to just use the 
  # key provided, simply supply 'default' (not case sensitive). Otherwise, we will expect 
  # the name of the key you are looking for. If you do not provide a full path to it, we will 
  # check in the running user's .ssh directory, however that isn't the best idea. You should
  # really just provide a full path
  # NOTE! If the user is a system_user (ie, no login), this will be ignored
  ssh_key: default
# Optional
dependencies:
# We will attempt to install the dependencies in this list regardless of the distro of the box we are on
- someprogram1
- someprogram2
- someprogram3
server_configuration:
  # Sets the hostname of the server to the provided hostname
  hostname: newhostname_for_server
  # Tells the system to update the server. Not case sensitive. If present, this will be run before anything else
  update: 'True'
  # Tells the system to upgrade the server distro. Not case sensitive
  upgrade: 'True'
  # Tells the system to disconnect and restart the server on completion. This is the very last thing ran, if present
  reboot_on_finish: 'True'
  # Services that we need to enable for the server. We expect the service(s) to be installed already. If its not, you're on
  # your own. Don't set us up for failure. 
  enable_service: 
    -someprogram1
    -someprogam2
configurations:
  # Optional
  # A list of scripts to execute in order on the server box.
  # Make sure that the server has the software installed to execute the script language though
  # 
  # You can additionally provide params for the system to obey when executing the script provided. You can also provide 
  # params to the script itself. We will consume the params we expect and pass all the rest to the script
  # The following params are reserved for us (meaning, if they are provided, we will consume then and they will not be passed along). None of these are case sensitive
  # --runAs=whatever user you want the script to be run as
  # --local tells us that you want the script to be locally (on the hosting box) instead of remotely. Note, we assume by default the scripts are to be
  #         run remotely. 
  #
  # You can also provide params for your script here, and those are passed to your script as well
  #
  # We pass the following additional params to every script that is run locally
  # --host=whatever the server ip is that we just finished our setup on
  # --user=whatever the user is that we used when initiating our connection to the server
  # --password=whatever the user's password is.
  # --ssh_key=whatever the ssh key is that was used to connect to the server. Note this is only provided if we were provided one
  # --ssh_passphrase=whatever the passphrase is for the key. Note this is only provided if we are provided it
- someFile1.py --runAs=root
- someFile2.pl --someparam=somevalue
- someFile3.sh

```