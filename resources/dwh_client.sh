#!/bin/bash
## Run the DWH gui client

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log_debug { [[ "${log_verbosity}" -ge 3 ]] && >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }
function log_info { [[ "${log_verbosity}" -ge 2 ]] && >&2 echo "[$(date +"$df")] {${script_name}} INFO: ${@}"; }
function log_warn { [[ "${log_verbosity}" -ge 1 ]] && >&2 echo "[$(date +"$df")] {${script_name}} WARN: ${@}"; }
function log_error { >&2 echo "[$(date +"$df")] {${script_name}} ERROR: ${@}"; }
>&2 echo "(stderr) logging verbosity set to: ${log_verbosity}"

## Add the venv python to PATH, so we use that over the system version (if it was created by install.sh)
client_basedir=$( dirname $(dirname "$(readlink -f "${BASH_SOURCE[0]}")") ) ## Parent of this "scripts" dir
[[ -d "${client_basedir}/.venv" ]] && source ${client_basedir}/.venv/bin/activate && log_info "Using python venv..."

## Check java and python are available
java -version > /dev/null 2>&1 || (echo "Java not available" && exit 1)
python --version > /dev/null 2>&1 || (echo "Python not available" && exit 1)

function is_j11 {
    ## Check if a path to java executable is java 11
    log_debug "Checking java option: ${1}"
    if type -p ${1} > /dev/null ; then
        j_ver=$(${1} -version 2>&1 | head -1 | cut -d'"' -f2 | sed '/^1\./s///' | cut -d'.' -f1)
        log_debug "java version is: ${j_ver}"
        if [[ ${j_ver} = '11' ]] ; then
            return 0
        fi
    fi
    return 1
}

## Ensure an appropriate java version is available 1st in the user's PATH
suitable_java="java"
if ! is_j11 ${suitable_java} ; then
    declare -a other_javas
    other_javas=($(find /usr/ -type f -name java 2> /dev/null | tr '\n' ' '))
    log_debug "Found #${#other_javas[@]} other javas: ${other_javas[@]}"
    for test_java in "${other_javas[@]}"; do
        # log "Test ${test_java}: $(is_j11 ${test_java}; echo $?)" 
        if is_j11 $test_java; then
            suitable_java=$test_java
            break
        fi
    done
fi
log_info "Using java: $suitable_java"
log_debug "$(${suitable_java} -version)"
export PATH=$(dirname ${suitable_java}):${PATH}

log_info "Testing java version:"
echo $PATH
java -version

## START
python3 src/dwh_client.py
## END

## Cleanup venv...
[[ -d "${client_basedir}/.venv" ]] && deactivate
log_info "DWH Client closed"
