#!/bin/bash

PLUGIN_ROOT_PY_PACKAGE_NAME=apitoolbox
source $(dirname $0)/ci_tools/mitto_plugins/ci_helpers.sh

build_static() { :; }  # for V2 plugins

run_test() {
    _activate_virtual_env
    make test
}

run_pylint() {
    _activate_virtual_env
    make pylint
}

_activate_virtual_env() {
    source $VIRTUAL_ENV/bin/activate
}

$@