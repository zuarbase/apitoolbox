#!/bin/bash

PLUGIN_ROOT_PY_PACKAGE_NAME=apitoolbox
source $(dirname $0)/ci_tools/mitto_plugins/ci_helpers.sh

build_static() { :; }  # for V2 plugins

run_test() {
    make test
}

run_pylint() {
    make pylint
}

$@