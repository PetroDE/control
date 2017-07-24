# Control

Control is a better Docker Compose. It allows you to control the building of Docker images, and starting containers for development and in a prod-like environment. Control understands using base images, building compile containers for generating artifacts to be put in your production images. Control allows you to define variables rather than needing a bootstrap script that sets up your environment then calls ```docker compose```. Control helps you mmanage image bloat, and works hard to ensure you're always building with the newest base image.

Control is portable. Control uses Python's executable zip, so not only can you have repeatable image builds with Dockerfiles, you can repeatably get the image built the same way, using the same version of Control. So you can "Keep absolutely everything in version control" as Jez Humble and David Farley suggest in *Continuous Delivery*.

Control should not be used to start containers in production. You should use a production-grade deployment system to do graceful swap-overs, and bleed connections from old releases. Control is best used on a developer's machine to build development images, and start development containers. But Control should also to be used in your CI to build the production ready images. This way a broken prod build can be diagnosed on a developers machine. There's no mystery sauce that goes into a production build when you can recreate it on a developer's machine. Use Control to start the production images on CI servers for testing if your production deploy system is awkward to configure for the volatile up/down nature of testing.

TL;DR: Control builds dev and prod images, and should be used to start dev testbeds, and can be a source of truth for how production images should be started. Don't use Control to start production images in production.

Control exit codes:  
1 - Control operation failed, check output  
2 - Something failed early (Docker daemon not started, malformed Controlfile)  
3 - Operation pre-check failed
