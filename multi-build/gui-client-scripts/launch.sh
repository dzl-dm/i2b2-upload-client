#!/bin/bash
## Run the PySide client from source (using venv if its there)

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

## See if venv already exists for this directory and activate it
client_basedir=$( dirname "$(readlink -f "${BASH_SOURCE[0]}")") ## Parent of this dir
[[ -d "${client_basedir}/.venv" ]] && . ${client_basedir}/.venv/bin/activate && log "Using python venv..."

function is_j118 {
    ## Check if a path to java executable is java 11
    log "Checking java option: ${1}"
    if type -p ${1} > /dev/null ; then
        j_ver=$(${1} -version 2>&1 | head -1 | cut -d'"' -f2 | sed '/^1\./s///' | cut -d'.' -f1)
        if [[ ${j_ver} = '11' || ${j_ver} = '8' ]] ; then
            return 0
        fi
    fi
    return 1
}

## Find java 11 (or 8) (else, just try the default and see)
suitable_java="java"
if ! is_j118 ${suitable_java} ; then
    declare -a other_javas
    other_javas=($(find /usr/ -type f -name java 2> /dev/null | tr '\n' ' '))
    log "Found #${#other_javas[@]} other javas: ${other_javas[@]}"
    for test_java in "${other_javas[@]}"; do
        # log "Test ${test_java}: $(is_j118 ${test_java}; echo $?)" 
        if is_j118 $test_java; then
            suitable_java=$test_java
            break
        fi
    done
fi
log "Using java: $suitable_java"
log "$(${suitable_java} -version)"

export compatible_java=${suitable_java}
${client_basedir}/src/gui/dwh_client.py

[[ -d "${client_basedir}/.venv" ]] && deactivate
