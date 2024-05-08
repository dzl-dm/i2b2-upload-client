#!/usr/bin/env bash
## Run the pseudonymisation on fhir bundle

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

## Add the venv python to PATH, so we use that over the system version (if it was created by install.sh)
client_basedir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")") ## Parent of this "scripts" dir
[[ -d "${client_basedir}/.venv" ]] && source ${client_basedir}/.venv/bin/activate && log "Using python venv..."

## Check python is available
python --version > /dev/null 2>&1 || (log "Python not available" && exit 1)

if [[ $# != 2 ]] ; then
    log "You must provide exactly 2 arguments; the path to the input and output fhir bundle files"
    exit 1
fi
## Check secret_key variable - disallow default "ChangeMe" and prompt if missing/empty
if [[ ! -n $secret_key || $secret_key = "ChangeMe" ]] ; then
    log "secret_key is default or not set, prompting for user input..."
    while true; do
        ## Default read with -s doesn't indicate any input is being registered - can be confusing, but is safer
        read -r -s -p "Please enter your secret_key (not visible):" secret_key_in
        ## Do some sort of sanity checks on key
        if [[ "$secret_key_in" =~ ^[A-Za-z][A-Za-z0-9\`\&\;\'\<\>_#$%@^~*+!?=.,:-]*$ && $secret_key_in != "ChangeMe" ]] ; then
            secret_key=$secret_key_in
            echo ""
            break
        else
            echo "Sorry, this name isn't valid, please try again..." >&2
        fi
    done
fi
export secret_key=${secret_key}
## use $1 and $2 as in/out file references. Py script will prompt for secret key
cat $1 | python ${client_basedir}/src/stream_pseudonymization.py > $2

## Deactivate pyhon venv if its there
[[ -d "${client_basedir}/.venv" ]] && deactivate
