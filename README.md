# RsyncDirector Deployment

A command line program for automating the deployment of [`rsyncdirector`](https://github.com/rchapin/rsyncdirector) instances.

## Install RsyncDirector Deployment

### Create a Virtual Environment
1. Ensure that there is a compatible version of Python installed. See `pyproject.toml` for details.

1. Export the path to the Python interpreter and the path to the virtenv and create and source the virtenv.
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

1. Install the wheel file
    ```
    pip install ./dist/rsyncdirector_deploy-<version>-py3-none-any.whl
    ```

1. Run `rsyncdirector_deploy -h` to confirm installation and to see details on how to run it.

### Distribute SSH Keys
The `rsyncdirector_deploy` program uses the Python [Fabric](https://www.fabfile.org/) library which depends on the Python [Paramiko](https://www.paramiko.org/) library for the core SSH protocol implementation to run commands on the remote hosts over SSH.  SSH connections are currently authenticated using passphrase-less SSH keys.

1. Distribute public SSH keys for the user under which you will run the deployment program on your localhost to the `root` user on the hosts on which you want to install `rsyncdirector`.

## Using the Deployment Tool to Install RsyncDirector
Following is an outline of the operations and commands required to run `rynscdirector`.  The `rsyncdirector_deployment` tool automates all of the following operations except the distribution of keys.

1. Create an `rsyncdirector.yaml` config file to define the data that you want to `rsync`.  See the [`rsyncdirector.yaml` file](https://github.com/rchapin/rsyncdirector/blob/main/rsyncdirector/resources/rsyncdirector.yaml) for a complete example with explanation.

1. Install Python on the target host:
    ```
    rsyncdirector_deploy python -h
    ```

1. Install `rsyncdirector` configs on the target host and optionally create an `rsyncdirector` user under which the application will run.  The user under which `rsyncdirector` runs MUST have read access to all data to be `rsync`ed.  In many cases, this can just be the `root` user to avoid having to create an additional user and ensure that the user has read access to all of the source data.
    ```
    rsyncdirector_deploy rsyncdirector configs -h
    ```

1. Install the `rsyncdirector` application
    ```
    rsyncdirector_deploy rsyncdirector install -h
    ```

1. Distribute SSH keys for the aforementioned user to the remote host(s) to which you will be syncing data
    Create ssh key pairs for the aforementioned user under which the `rsyncdirector` will run and distribute the public keys to the users on the remote hosts to which you will be syncing data.

    Best practice is to create a non-root user on the remote host to which data will be synced and then have create an `rsyncdirector` configuration that connects using that user.

    For example: in order to be able to read any files on the source host, run the `rsyncdirector` as root.  On the remote host to which data is to be synced create a `backup` user and create a directory where the `backup` users has `r-w-x` permissions.  Create an ssh key-pair for the `root` user on the localhost and distribute the public key to the remote host adding it to the `backup` user's `authorized_keys` file.

## Development
Do the following if you want to develop and debug the installation scripts using VSCode.

1. Create a virtual environment as described in the Setup section above.
1. Pip install the additional `requirements_dev.txt` dependencies.
1. Add the `deployment` directory to VSCode.
1. Click on the Debug tab and select from one of the launch configuratons defined in the `launch.json` file.  You must have the `main.py` file selected in the IDE before clicking on the Debug play button.

