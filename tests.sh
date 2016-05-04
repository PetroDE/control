#!/usr/bin/env bash

for testfile in test_*.py; do
    py.test -v --junitxml results_${testfile:5:-3}.xml $testfile
done
exit 0
