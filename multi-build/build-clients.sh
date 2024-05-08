#!/bin/bash

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
client_basedir="$(dirname ${script_name})/.."
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }
log "Client basedir: ${client_basedir}"

function build_cli_client_package {
    ## Zip everything we need to run the source (java binary/jar) on windows/linux cli
    ## Include java and python components
    ## Include "installer" script - add pip requirements and check pre-requisites
    ## Include scripts for local processing and DWH processing
    log "Building the cli client package..."

    ## Copy from other parts of the project
    mkdir -p tmp/cli-client/src
    cp -a ../src/* tmp/cli-client/src/
    ## Remove the unused "process-pid.py" script, it relied on XSLT v2 which isn't stream capable, so can't handle large files.
    ## The file isn't removed because it should be developed into XSLT v3, which could then supersede the python version currently in use
    rm tmp/cli-client/src/process-pid.py
    cp -a cli-client-scripts/* tmp/cli-client/
    cp -a ../resources/lib tmp/cli-client/
    ## Convert the markdown ReadMe to more universal HTML
    pandoc -f markdown ../README.md > tmp/cli-client/README.html

    ## Build the archive
    cd tmp
    rm ../../dist/cli-client.zip
    zip -r ../../dist/cli-client.zip cli-client/
    cd -
    log "cli client package now available under: '${client_basedir}/dist/cli-client.zip'"
}

function build_src_gui_client_package {
    ## Zip everything we need to run the PySide GUI from source (with java binary/jar)
    ## Include "installer" script - add pip requirements and check pre-requisites
    log "Building the GUI (source) client package..."

    ## Copy from other parts of the project
    mkdir -p tmp/gui-client/
    cp -a gui-client-scripts/* tmp/gui-client/
    cp -a ../src tmp/gui-client/
    rm tmp/gui-client/src/process-pid.py
    cp -a ../resources tmp/gui-client/
    ## Build the py class(es) from .ui file(s)
    pyside6-uic ../src/gui/mainWindow.ui -o tmp/gui-client/src/gui/ui_mainwindow.py

    ## Convert the markdown ReadMe to more universal HTML
    pandoc -f markdown ../README.md > tmp/gui-client/README.html

    ## Build the archive
    cd tmp
    rm ../../dist/gui-client.zip
    zip -r ../../dist/gui-client.zip gui-client/
    cd -
    log "GUI (source) client package now available under: '${client_basedir}/dist/gui-client.zip'"
}

function build_exe_gui_client_package {
    ## Use wine to build a windows .exe of the GUI - it still calls java externally
    ## TODO: Confirm if it needs python given the way it calls steam_pseudonym
    log "Building the GUI (.exe for windows) client package..."

    ## Trusting we're already in the venv
    pyside6-uic ../src/gui/mainWindow.ui -o ../src/gui/ui_mainwindow.py
    ## Build windows exe (pyinstaller will put the artefact in dist/)
    cd ..
    wine64 pyinstaller dwh_client.spec
    cd -

    log "GUI (.exe for windows) client package now available under: '${client_basedir}/dist/dwh_client.exe'"
}

function build_linux_gui_client_package {
    ## Build linux binary of the GUI - it still calls java externally
    ## TODO: Use manylinux docker image to build version compatible with older glibc
    log "Building the GUI (binary for linux) client package..."

    ## Trusting we're already in the venv
    pyside6-uic ../src/gui/mainWindow.ui -o ../src/gui/ui_mainwindow.py
    ## Build linux binary (pyinstaller will put the artefact in dist/)
    cd ..
    pyinstaller dwh_client.spec
    cd -

    log "GUI (binary for linux) client package now available under: '${client_basedir}/dist/dwh_client'"
}

## Check for the build venv... (we need it to build the GUI)
type deactivate 2>/dev/null || { [[ -d "${client_basedir}/.venv" ]] && . ${client_basedir}/.venv/bin/activate && log "Using python venv..."; } || log "I don't see a venv, check that is correct?"

## Build each client, then cleanup...
log "Building clients..."
build_cli_client_package
build_src_gui_client_package
# build_exe_gui_client_package
# build_linux_gui_client_package

## Convert the markdown ReadMe to more universal HTML
pandoc -f markdown ../README.md > ${client_basedir}/dist/README.html

## Remove copied/build files
log "Cleaning up temp/build..."
rm -rf tmp

log "Clients available under ${client_basedir}/dist/"
