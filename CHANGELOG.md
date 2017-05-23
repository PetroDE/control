## 2.4.1

* [FEATURE] New variable for interpolation: RANDOM will be unique for most places in a Controlfile
* [FEATURE] New variable for interpolation: CONTROL_SESSION_UUID unique for each control run

## 2.4.0

* [FEATURE] Ability to have different volumes mounted into containers between dev and prod

* [ENHANCEMENT] If a host binding cannot be created, an error is shown with the volume in error instead of showing an HTTP 500 error.
* [ENHANCEMENT] Stronger underlying mechanisms for constructing different service types
* [ENHANCEMENT] Strongly defined and tested Option substitution in Metaservices

* [BUGFIX] Does not attempt to pull from Docker Hub images that were just built
* [BUGFIX] Moved wrong warning that image does not exist in registry to different logging level
* [BUGFIX] Running commands works in prod containers works
* [BUGFIX] control start --dump now includes the --detach flag
