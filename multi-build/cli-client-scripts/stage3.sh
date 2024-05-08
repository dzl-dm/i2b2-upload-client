#!/usr/bin/env bash
## Run the api processing (wrap the python script so we use venv if needed)

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

## Add the venv python to PATH, so we use that over the system version (if it was created by install.sh)
client_basedir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")") ## Parent of this "scripts" dir
[[ -d "${client_basedir}/.venv" ]] && source ${client_basedir}/.venv/bin/activate && log "Using python venv..."

## Check python is available
python --version > /dev/null 2>&1 || (log "Python not available" && exit 1)

## Just pass through any options/arguments...
python ${client_basedir}/src/api_processing.py $*

## Deactivate pyhon venv is its there
[[ -d "${client_basedir}/.venv" ]] && deactivate
