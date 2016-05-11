#!/usr/bin/env bash

for testfile in tests/test_*.py; do
    py.test -v --junitxml results_${testfile:11:-3}.xml $testfile
done
exit 0
