#!/bin/bash
## Install python requirements (setting up venv as necessary)

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

## Check python is available
python --version > /dev/null 2>&1 || (log "Python not available" && exit 1)
## Check java is available
java -version > /dev/null 2>&1 || (log "Java not available" && exit 1)

## See if venv already exists for this directory and activate it
client_basedir=$( dirname "$(readlink -f "${BASH_SOURCE[0]}")") ## Parent of this "scripts" dir
[[ -d "${client_basedir}/.venv" ]] && . ${client_basedir}/.venv/bin/activate && log "Using existing python venv..."

## Install python libraries
if ! pip install -r src/requirements.txt > /dev/null 2>&1 ; then
    log "Cannot use pip directly (system-wide), creating venv..."
    python -m venv ./.venv
    ./.venv/bin/pip install -r src/requirements.txt
fi
[[ -d "${client_basedir}/.venv" ]] && ./.venv/bin/pip install -r src/gui/requirements.txt || pip install -r src/gui/requirements.txt

log "DWH Upload Client installation complete"
log "You can now launch the GUI client under:\n ${client_basedir}/launch.sh"
