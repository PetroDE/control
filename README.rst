PetroDE Control script
  It does stuff(TM)

A script to build Docker images, compile code, run tests, be friendly to
developers, enable local development, check in build configuration next to
code, kiss babies, and be popular.

We really don't expect much of it. /s

Control is a general use build tool. But, it is a developer specific container
support tool. Control should not be used to start images in production.

Exit codes:
1 - Control operation failed, check output
2 - Something failed early (Docker daemon not started, malformed Controlfile)
3 - Operation pre-check failed
