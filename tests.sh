#!/usr/bin/env bash

for testfile in control/tests/test_*.py; do
    py.test -v --junitxml results_${testfile:19:-3}.xml $testfile
done
exit 0
