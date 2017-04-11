## 2.4.0.alpha10

* [ENHANCEMENT] If a host binding cannot be created, an error is shown with the volume in error instead of showing an HTTP 500 error.

## 2.4.0.alpha9

* [BUGFIX] control start --dump now includes the --detach flag

## 2.4.0.alpha8

* [BUGFIX] Fix crash when trying to build a service that does not define a pre-build event

## 2.4.0.alpha7

* [BUGFIX] Variable and Option substitution works, and has tests

## 2.4.0.alpha4

* [BUGFIX] Unioning volumes works again with split shared/dev/prod volumes

## 2.4.0.alpha3

* [BUGFIX] Metaservice list correctly substitutes concrete services

## 2.4.0.alpha2

* [BUGFIX] Running commands works in prod containers works

## 2.4.0.alpha1

* [FEATURE] Ability to have different volumes mounted into containers between dev and prod
* [ENHANCEMENT] Stronger underlying mechanisms for constructing different service types
