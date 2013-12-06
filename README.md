# dockerctl

A tool for managing docker containers using per-container config files

## Usage:

Since the `docker` command needs root privileges for most commands, we need to
use `sudo` all the time to invoke `dockerctl` commands.

Let’s define a container called „webserver“ that‘s based on an image called
„apache2“. Copy the example configuration from below into the file
`/etc/dockerctl/webserver.conf`.

### Starting a container
Use the command `dockerctl start CONTAINER` to start the container:

    $ sudo dockerctl start webserver

The container is now running and you can access just as a usual docker
container.

### Showing the status

The command `dockerctl status` shows the status of all defined containers:

    $ sudo dockerctl status
    CONTAINER:  webserver
    Id:         bfd1c4eb31a5
    Name:       condescending_ritchie
    Command:    /usr/sbin/apache2 -D FOREGROUND -X
    Created:    Yesterday
    Started:    Yesterday
    IP address: 172.17.0.116
    Ports:      0.0.0.0:8080 -> 80/tcp
    Volumes:    /var/log/apache2 -> /srv/webserver/log
                /var/www -> /srv/webserver/www

or, if the container is not running, the output might be:

    Container webserver is not running

### Stopping a container

To stop a container, use:

    $ sudo dockerctl stop webserver
    Stopping webserver ... done

## Example configuration

Example configuration file for the above webserver example:

    {
    "image": "apache2",
    "volumes": [
        {
        "host_dir": "/srv/webserver/www",
        "container_dir": "/var/www"
        },
        {
        "host_dir": "/srv/webserver/log",
        "container_dir": "/var/log/apache2"
        }
    ],
    "ports": [
        {
        "host_port": 8080,
        "container_port": 80
        }
    ]
    }

## Building a Debian package

You‘ll need the „Python to Debian source package conversion utility” stdeb:

    pip install stdeb

Then, you can create the Debian package like so:

    ./setup.py --command-packages=stdeb.command sdist_dsc bdist_deb

You can adjust the version in the file `VERSION` and the Debian package version
in setup.cfg.

After this, the package lies in `deb_dist` and you can install using `dpkg`:

    dpkg -i deb_dist/mypackage_0.1-1_all.deb
