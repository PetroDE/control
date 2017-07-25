`control` is a program that builds docker containers.

Functions
---------

Control has many functions that it performs. Its most basic usage is to `build` images, `start` and `stop` containers. There are some nice shorthand for combinations of these functions.

| Function     | Notes                                                                                                                                                                                                       |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `build`      | Builds an image for development environments                                                                                                                                                                |
| `build-prod` | Builds an image for production environments                                                                                                                                                                 |
| `start`      | Starts a container                                                                                                                                                                                          |
| `stop`       | Stops a container                                                                                                                                                                                           |
| `restart`    | Ensures the container is removed and then starts the container                                                                                                                                              |
| `rere`       | Rebuilds the image, and then restarts the container with the new image                                                                                                                                      |
| `open`       | Restarts the container but lands you in a shell session in the container as process 1                                                                                                                       |
| Commands     | In your Controlfile you may specify a list of commands that you might want to run inside a container and see the output. You specify the one word command that you use to run the program in the container. |

### Commands

You may, in your Controlfile, specify a list of commands to be run in a container. If the container is not running, Control will start the container and run the command inside it, and remove the container after the command exits. If the container is running, Control will simply exec the command into the container, and return the output to you. You may, optionally, specify `-r` on the command line and Control will kill your container and bring it back up with only the command running inside the container, this way there are no other processes running that could interfere with the script. When you specify `-r` after the command is run, the container will be restarted using its default entrypoint.

Extra arguments may be passed to the command by appending them to the control run as such:

``` bash
control test SERVICE -- ARGS_PASSED_THROUGH
```

These extra arguments must come after a `--` flag. Anything before the dash-dash flag will be interpreted as arguments to Control itself.

Events
------

*Full article at [ControlfileReference.md#events](ControlfileReference.md#events)*

The primary failing of `docker build` is that it assumes that all the files that should go into an image exist somewhere recursively inward from the Dockerfile. But then any file that exists at a layer boundary will always exist in that image, even if it's deleted in a later layer. Because of this you must change your thinking of how to get an application installed in a container. It's stupid to copy source code into an image then run a compile. You've ballooned the size of your image because you have the source code, the tools to build the source code, and the resultant output when all you need is the output.

So, a compile container should be used that has all the build tools, then mount in the source code, and mount the build destination. This way you can take only the output and build it into a new skinny image that has only what it needs.

This is the purpose of Control. To be an easy tool to keep people in the mindset of using a compile container to only keep artifacts.

The “prebuild” event is a scriptable endpoint that allows you to start a compile container that builds what eventually goes into the final output image.

Pip dependencies
----------------

-   `docker-py`
-   `python-dateutil`

Work still Remaining
--------------------

-   Prettier `docker pull` output
-   Figure out a good way to designate a 'latest' with rich tagging
-   bash and zsh completion
-   allow comments in Controlfiles

Behaviors
---------

### Default

If control is not given a specific action to perform it will attempt a build of the image, and then start the container.

### Build

`build` will pass along the build request to the docker daemon. Unless specified with `--no-cache` Docker will be free to decide to use the cache if it thinks it can. Unless the image is based off of an image on the Docker Hub it will pull a newer version of the base image if one exists.

### Start

start will start a container if a container by that name is not running currently, or if it can determine the options that were used to create the container are different, or if the image it is running is out of date (locally only, it won't check if there's newer on the remote).

### Restart

`restart` will always restart a container. If there is a new image it will kill the current container and start the container with the new image.

Pulling base images
-------------------

Control attempts to make sure that an image is always built with the latest components. Even the base image. There's a problem with this though. The Docker Hub does not have an accessible API. It's less than useless. There's no way to get anything about the image other than its ID. Self hosted registries are different. Apparently Docker had some notion that people might try to use their code in their own projects.

Options:

-   `--pull` will always attempt to pull the image specified in the `FROM` line. The program will error out if the upstream base image does not exist.
-   `--no-pull` will never pull an image. No checks will be made about if the image is out of date. The program will error out if the image does not exist.
-   Specifying neither option will use the default behaviour
    -   `control build` will perform a check and print out the result but will pull if it can determine that the local image is older than the upstream image. In the case of images that exist in the hub, but the ID's do not match a warning will be printed; `--pull` must be specified to pull from the hub.
    -   `control build-prod` will pull from the upstream if a registry is specified, and will only attempt to pull from the Hub if the image exists in the Hub.

Controlfile Reference
---------------------

*Full definition at [ControlfileReference.md](ControlfileReference.md)*

``` javascript
{
    "image": "influxdb:0.9.6.1",
    "container": {
        "expected_timeout": 5,
        "tty": false,
        "detach": true,
        "name": "influxdb.{collective}",
        "hostname": "influxdb",
        "volumes": [
            "/var/lib/influxdb/{collective}/:/var/lib/influxdb/:rw",
            "/mnt/log/{collective}/influxdb/:/var/log/influxdb/"
        ]
    }
}
```

The list of volumes should be specified according to the Docker volume naming rules. You cannot create transient volumes in the Controlfile.
