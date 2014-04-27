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

    image: apache2
    ports:
    -
        container_port: 80
        host_port: 8080
    volumes:
    -
        container_dir: /var/www
        host_dir: /srv/webserver/www
    -
        container_dir: /var/log/apache2
        host_dir: /srv/webserver/log

## Building a Debian package

Change current working directory to project root and run

    fakeroot dpkg-buildpackage -uc -us

After this, there should be a Debian package in the parent directory
including the whole virtualenv.
