# RsyncDirector Deployment

A command line program for automating the deployment of [`rsyncdirector`](https://github.com/rchapin/rsyncdirector) instances.

## Install RsyncDirector Deployment

### Create a Virtual Environment
1. Ensure that you have a compatible version of Python installed. See `pyproject.toml` for details.
1. Export the path to your Python interpreter and the path to our virtenv and create and source the virtenv.
    ```
    export PYTHON_PATH=<path-to-your-interpreter>
    export VIRT_ENV_PATH=<path-to-virt-env-parent-dir>
    $PYTHON_PATH -mvenv $VIRT_ENV_PATH
    . $VIRT_ENV_PATH/bin/activate
    ```

### Install install from PyPi or build and install from the `.whl` file.

#### From PyPi
```
pip install rsyncdirector_deploy
```

#### Build and Install from Wheel
1.  Build
    ```
    pip install -r ./requirements_dev.txt && \
    python -m build && \
    twine check dist/*
    ```

1. Install the wheel file now ind the `dist/` dir
    ```
    pip install ./dist/rsyncdirector_deploy-<version>-py3-none-any.whl
    ```

1. Run `rsyncdirector_deploy -h` to confirm installation and to see details on how to run it.

## Using Deployment Tool to Install RsyncDirector

Following are the big pieces required to run `rynscdirector`
1. Create an optional `rsyncdirector` user on the host where you want to install it
1. Distribute SSH keys for the aforementioned user to the remote host(s) to which you will be `rsync`ing data
1. Build an `rsyncdirector.yaml` config file to define the data that you want to `rsync`
1. Deploy `rsyncdirector` configurations
1. Install the `rsyncdirector` application

### Creation of `rsyncdirector` user
The user under which `rsyncdirector` runs MUST have read access to all data to be `rsync'ed.  In many cases, this can just be the `root` user to avoid having to create an additional user and ensure that the user has read access to all of the source data.




## Setup
1. Distribute public SSH keys for the user under which you will run the deployment program on your localhost to the `root` user on the hosts on which you want to install `rsyncdirector`.
1. Export the path to a compatible version of Python
    ```
    export PYTHON_PATH=<path-to-python>
    ```
1. Create a virtual environment with an appropriate version of Python.  See the `pyproject.toml` file for the required version.  Change directories to the root of the `deployment` directory.
    ```
    $PYTHON_PATH -mvenv ~/.virtualenvs/rsyncdirector_deployment && \
    . ~/.virtualenvs/rsyncdirector_deployment/bin/activate && \
    pip install -r ./requirements.txt
    ```
1. Run `deploy-rsyncdirector -h` to ensure it works correctly.

## Installation

1. Install Python on the remote host:  Run `deploy-rsyncdirector python -h` for details.
1. Install `rsyncdirector` configs on the target host: Run `deploy-rsyncdirector rsyncdirector configs -h` for details.
1. Install `rsyncdirector` application on the target host: Run `deploy-rsyncdirector rsyncdirector install -h` for details.

Once installed, on the hosts on which you installed `rsyndirector` you will need to distribute SSH keys for the user under which the `rsyncdirctor` program is running on the hosts to which you will be `rsync`ing data.  The deployment program will create the user with the `/usr/sbin/nologin` shell specified, so to generate a set of keys, you will need to run the following, as root, on that host
```
sudo -u rsyncdirector ssh-keygen
```
Once you have your key pair, distribute the public key to the user and hosts to which you want to `rsync` data and make sure to ssh and accept the fingerprint.
```
sudo -u rsyncdirector ssh <user-name>@<remote-host> "ls"
```

## Development
Do the following if you want to develop and debug the installation scripts using VSCode.

1. Create a virtual environment as described in the Setup section above.
1. Pip install the additional `requirements_dev.txt` dependencies.
1. Add the `deployment` directory to VSCode.
1. Click on the Debug tab and select from one of the launch configuratons defined in the `launch.json` file.  You must have the `main.py` file selected in the IDE before clicking on the Debug play button.

