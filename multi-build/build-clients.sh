#!/bin/bash

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }
# client_basedir="$(dirname ${script_name})/.."
client_basedir="$(cd $(dirname ${BASH_SOURCE[0]})/.. && pwd)"
log "Client basedir: ${client_basedir}"
cd "${client_basedir}/multi-build"
log " > Working from multi-build/ dir"

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
    # pandoc -f markdown ../README.md > tmp/cli-client/README.html
    cp ${client_basedir}/dist/README.html tmp/cli-client/README.html

    ## Build the archive
    cd tmp
    rm ../../dist/client-command-line.zip
    zip -r ../../dist/client-command-line.zip cli-client/
    cd -
    log "cli client package now available under: '${client_basedir}/dist/client-command-line.zip'"
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

    ## Convert the markdown ReadMe to more universal HTML
    # pandoc -f markdown ../README.md > tmp/gui-client/README.html
    cp ${client_basedir}/dist/README.html tmp/gui-client/README.html

    ## Build the archive
    cd tmp
    rm ../../dist/client-source.zip
    zip -r ../../dist/client-source.zip gui-client/
    cd -
    log "GUI (source) client package now available under: '${client_basedir}/dist/client-source.zip'"
}

function build_exe_gui_client_package {
    ## Use wine to build a windows .exe of the GUI - it still calls java externally
    ## TODO: Confirm if it needs python given the way it calls steam_pseudonym
    log "Building the GUI (.exe for windows) client package..."

    ## Build windows exe (pyinstaller will put the artefact in dist/)
    cd ..
    uv run wine pyinstaller dwh_client.spec
    mv dist/dwh_client.exe dist/dwh_client_windows.exe
    cd -

    log "GUI (.exe for windows) client package now available under: '${client_basedir}/dist/dwh_client_windows.exe'"
}

function build_linux_gui_client_package {
    ## Build linux binary of the GUI - it still calls java externally
    ## TODO: Use manylinux docker image to build version compatible with older glibc
    log "Building the GUI (binary for linux) client package..."

    ## Build linux binary (pyinstaller will put the artefact in dist/)
    cd ..
    uv run pyinstaller dwh_client.spec
    mv dist/dwh_client dist/dwh_client_linux
    cd -

    log "GUI (binary for linux) client package now available under: '${client_basedir}/dist/dwh_client_linux'"
}

function compile_gui {
    ## Convert the QT Designer file into a python file
    output_dir=${1:-../src/gui}

    ## Build the py class(es) from .ui file(s)
    uv run pyside6-uic ../src/gui/mainWindow.ui -o ${output_dir}/ui_mainwindow.py
    log "GUI source '../src/gui/compiled mainWindow.ui' -> '${output_dir}/ui_mainwindow.py'"
}
function update_version_file {
    ## Ensure the static "version.txt" file used for binaries is updated to reflect the pyproject.toml version
    cd ${client_basedir}
    python3 -c "import toml; my_pyproject = toml.load('pyproject.toml'); version = my_pyproject['project']['version']; print('Setting version: ', version); open('build/version.txt', 'w').write(version);"
    cd -
}
function convert_icon {
    cd ${client_basedir}
    magick resources/DzlLogoSymmetric.webp -resize x64 -gravity center -crop 64x64+0+0 -flatten -colors 256 -background transparent resources/DzlLogoSymmetric.ico
    cd -
}

## Check for the build venv... (we need it to build the GUI)
type deactivate 2>/dev/null || { [[ -d "${client_basedir}/.venv" ]] && . ${client_basedir}/.venv/bin/activate && log "Using python venv..."; } || log "I don't see a venv, check that is correct?"

## Convert the markdown ReadMe to more universal HTML
log "Compiling documentation..."
pandoc -f markdown "${client_basedir}/README.md" > "${client_basedir}/dist/README.html"

log "Syncing version numbers..."
update_version_file
convert_icon
log "Compiling GUI..."
compile_gui

## Build each client, then cleanup...
log "Building clients..."
build_cli_client_package
build_src_gui_client_package
build_exe_gui_client_package
build_linux_gui_client_package

## Remove copied/build files
log "Cleaning up temp/build..."
rm -rf tmp

log "Clients available under ${client_basedir}/dist/"
