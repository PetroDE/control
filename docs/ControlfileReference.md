Controlfiles were originally meant to be a drop dead simple way of defining how a container should be started and the image tag that should be used for building and starting. It got a little more complex. So here's documentation on how all the little bits get interpreted when they don't exist, when they do exist, and when they have multiple definitions.

Two kinds of Services
---------------------

There are two kinds of services that may exist in a Controlfile. A Metaservice definition, which defines a list of services, and transformations that may applied to the full list. A service definition defines how an image will be built, and how containers based on an image may be started.

### Metaservices

All services that are ever referenced must be eventually defined.

A Metaservice is defined by having a list of services. As below:

``` javascript
{
    "services": ["foo", "bar"]
}
```

If a service object does not have a “services” key, it is not a Metaservice. It is a Uniservice.

A Uniservice looks like this:

``` javascript
{
    "image": "busybox:latest"
}
```

A Metaservice may define Uniservices:

``` javascript
{
    "services": {
        "foo": {
            "image": "busybox:latest"
        }
    }
}
```

A Metaservice may reference another Controlfile to fill the definition of any kind of service:

``` javascript
# ./Controlfile
{
    "services": {
        "meta": {
            "controlfile": "meta/Controlfile"
        }
        "foo": {
            "controlfile": "foo/Controlfile"
        }
    }
}
# ./meta/Controlfile
{
    "services": {
        "lorem": {
            "image": "busybox:latest"
        }
    }
}
# ./foo/Controlfile
{
    "image": "busybox:latest"
}
```

Be aware that if a service definition references a controlfile, Control immediately reads in that controlfile and switches to using that Controlfile to define the service. It discards any parameters that were defined previously.

### Uniservice

To be absolutely clear a service that is not a Metaservice is called a Uniservice. However, for the majority of cases when you say “Service” you'll be talking about a Uniservice, and when you say “Services” you mean just a set of Services. But, the term is there for those when you need to be ultimately clear.

A Service definition includes the differences between a development and production build. Since Control is not meant to be used to start a container in production, the Container definition needs only be concerned with development.

The First Controlfile
---------------------

Now that you know that there are 2 kinds of Services, the first Controlfile Control reads in is treated just a little bit special.

If the first Controlfile is a Uniservice, it is added to a metaservice called 'all'.

If the first Controlfile is a Metaservice, that service is treated as the definition of 'all'.

If you want to run Control on a project that only has one container, but you want to use more variables than the default set or if you want to use option transformation for some reason, make your Controlfile a Metaservice that defines your one Service inline. There's no rule that a Uniservice has to live in its own file. It's easier to read when you have lots of services, but there's no rule stopping you.

Service Definition Pairs
------------------------

These are valid options for a Controlfile:

| Option                | P/D | Description                                                                                                                                                                                                                                                                       |
|-----------------------|-----|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `image`               | Y   | Specify an image name. Depending on if a Dockerfile exists, the image will be pulled or built.                                                                                                                                                                                    |
| `dockerfile`          | Y   | Control will guess that there is a file named `Dockerfile` (or `Dockerfile.dev` and `Dockerfile.prod`) in the same directory as the Controlfile that defined the service. If you don't conform to this naming scheme, set this to the path to the Dockerfile to build the image.  |
| `fromline`            | Y   | Specifying this will modify the FROM line of the Dockerfile will be changed to the string specified.                                                                                                                                                                              |
| `open`                | -   | Normally a container is run detached. But it can be useful to be inside the container to run scripts before anything else starts. `open` allows you to specify a shell you would like to have run interactively instead of detaching the container and getting a shell afterward. |
| `expected_timeout`    | -   | If the container does not behave itself and shut down when it gets a signal from docker to gracefully end itself you can override docker's default timeout of 10 seconds. This can also be useful if the container takes longer to halt than 10 seconds.                          |
| `env_file`            | -   | Sometimes you want to pass values to a container that you don't want checked in. Put those into an env file and point this value at it.                                                                                                                                           |
| `required`/`optional` | -   | Setting required to true (or optional to false) will add the service to the required metaservice. This way control commands that don't specify a list of services can have a default list.                                                                                        |
| `events`              | O   | Control only wraps up docker commands because they're obnoxious to type and memorize. If you need a script run at certain points in a Control command, specify the script and arguments here. More details, and supported events can be read in [Events](#Events).                |
| `commands`            | -   | To aid in testing, it is possible to execute a command inside of a container (whether the container is already running or not). Specify the command name and script to run inside the container as pairs here. The star command allows a catch-all command to be run.             |
| `container`           | -   | This must be set to an object that defines all the options that will be passed to docker to create the container.                                                                                                                                                                 |

### Prod and Dev Variants

Some of the pairs you may specify in a Service allow for different values to be specified depending on if the image will be built/used in a development or production-like manner.

The pairs in the table with a `Y` in the P/D column in the above table are the options that allow this difference to be specified.

In most cases, there is no need to treat an option differently based on the kind of container it is, in fact it's better the fewer differences there are. These options should be specified normally.

``` javascript
 {"fromline": "myimage:{COLLECTIVE}"}
 ```

 ``` javascript
 {
     "events": {
         "prebuild": "make clean"
     }
 }
 ```

But when there are necessary differences between what is used in production and development (installing testing tools into a development container by using a development Dockerfile) specify a “dev” and “prod” variant.

``` javascript
{
    "dockerfile": {
        "dev": "Dockerfile.dev",
        "prod": "Dockerfile.prod"
    }
}
```

This isn't the best example, since Control will automatically guess this variant in the event that a file named “Dockerfile” exists. However, if you do have a file named Dockerfile in the directory, you will have to explicitly override and specify that there are Dockerfiles for dev and prod builds.

You may also elect to only specify one of the variants if nothing should be done for the other image type.

``` javascript
{
    "events": {
        "prebuild": {
            "prod": "make clean"
        }
    }
}
```

Transformation Options
----------------------

Control offers 2 features that enable flexibility in service definitions, that together introduce an incredible amount of complexity with nooks for crazy cool superpowers to manifest unknown even to the original developer!

### Variable Interpolation

Control allows for individual options to accept a variable that will be interpolated in at run time.

``` javascript
{
    “services”: {
        “image”: “service1:latest”,
        “container”: {
            “volumes”: [
                “{LOG_DIR}/js/service1”
            ]
        }
    },
    “vars”: {
        “LOG_DIR”: “/mnt/log”
    }
}
```

#### Provided Variables

Control offers some variables that may prove useful.

-   CONTROL\_DIR - The directory of the main Controlfile
-   CONTROL\_PATH - The path to the Control executable
-   CONTROL\_SESSION\_UUID - Every control run generates a unique ID
-   HOSTNAME - If this environment variable does not exist, populated with the output of the `hostname` command.
-   RANDOM - This is a unique random value each time it is substituted in (not cryptographically strong)
-   UID - the current user's UID
-   GID - The current user's first group (not every environment exports a GID, so control ensures it exists)

Control is also git aware. If you are in a git repo, these variables will also be available to you.

-   GIT\_BRANCH
-   GIT\_COMMIT
-   GIT\_ROOT\_DIR
-   GIT\_SHORT\_COMMIT

Control also allows interpolation of any Environment Variables. If a variable declared in a Controlfile also exists in your environment, Control will prefer the environment.

### Option Substitution

Control also offers the ability to define option transformations that may be applied. There are 4 transformations.

-   Prefix - Anything specified will be set before any existing options, String/string prefixes will be prefixed as one string, list/\* the options will be transformed into lists
-   Suffix - Anything specified will be set after any existing options, following the same rules as prefix
-   Union - Lists will be joined and redundancy between the two lists will be removed (prefering definitions before your controlfile)
-   Replace - Anything you specify on your outer controlfile level will completely replace whatever was specified anywhere inside of the controlfiles you reference

Option substitutions are specified within a block for the option that you are substituting.

``` javascript
{
    “services”: {
        “image”: “service1:latest”,
        “container”: {
            “name”: “service1”
        }
    },
    “options”: {
        “name”: {
            “suffix”: “.username”
        },
        “volumes”: {
            “replace”: [
                “/mnt/log/foo/bar:/mnt/log”
            ]
        }
    }
}
```

#### Using Option Substitution judiciously

Sometimes you may not want to wholesale replace an option on all containers defined in all nested controfiles. In this case you reference your controlfile, and define a nested metaservice that just defines a list of services, and options.

``` javascript
{
    “services”: {
        “most”: { “controlfile”: “relative/path/to/Controlfile” },
        “judicious”: {
            “services”: [
                “service1”,
                “service2”
            ],
            “options”: {
                “name”: {
                    “suffix”: “.username”
                },
                “volumes”: {
                    “replace”: [
                        “/mnt/log/foo/bar:/mnt/log”
                    ]
                }
            }
        }
    }
}
```

FROM Line
---------

To support having a collective specific base image that is built as part of the build process it was necessary to have the ability to rewrite the `FROM` line of a Dockerfile. `docker build` MUST be given a path to a Dockerfile, it will not read from an input stream. `docker build` allows you to specify variables to substitute into a Dockerfile at build time, but doesn't allow this substitution to occur on the `FROM` line. This needs to be accomplished in a way that doesn't leave the original Dockerfile as an unstaged change in git. So Control reads the whole Dockerfile into a temporary file. When it counters the `FROM` line, if you have set `fromline` that line is put into the temporary file.

This solution was chosen so that the Dockerfile that is being transformed can be left in a mostly reasonable state for manual runs of `docker build`.

Events
------

Control allows you to run a script of your choosing at certain points during its run. Currently there are only two events:

-   prebuild
-   postbuild

These events are always run at the location of the Controlfile that defined the service that the event is tied to. So, a prebuild event for service1 will be forked from the `containers/service1` directory if you have your repo structured as:

```
root
  - other-directories
  - containers
    - service1
      - Dockerfile
```

Events may be a string that will be run for every build type, or it may be an object that defines a mapping of build types to scripts to run. If a mapping does not exist, then no event will be run for that build type. For example,

``` javascript
{
    "events": {
        "prebuild": {
            "dev": "make dev"
        }
    }
}
```

defines a prebuild that will be run when `control build` is called.

Remember that the Controlfile has been read in and normalized already. If you use prebuild to generate a Dockerfile where one did not exist before, then when the Dockerfile location was guessed, because it did not exist no Dockerfile location was set. To fix this, you should explicitly define the location of the Dockerfile for your service.

``` javascript
{
    "image": "example:latest",
    "dockerfile": "Dockerfile",
    "events": {
        "prebuild": {
            "prod": "make"
        }
    }
}
```

If `dockerfile` was not defined, and `Dockerfile` did not exist, then Control would interpret the Controlfile to have been defined as “`dockerfile`”`: "",`, and then would not allow you run `control build` or `control build-prod` for that service.
