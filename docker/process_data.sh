#!/usr/bin/env bash
## Process data into fhir format

## Hacky fix for cases when script run from a dir that doesn't seem to exist
cd /tmp

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

function is_j11 {
    ## Check if a path to java executable is java 11
    log "Checking java option: ${1}"
    if type -p ${1} > /dev/null ; then
        j_ver=$(${1} -version 2>&1 | head -1 | cut -d'"' -f2 | sed '/^1\./s///' | cut -d'.' -f1)
        if [[ ${j_ver} = '11' ]] ; then
            return 0
        fi
    fi
    return 1
}

## Find java 11 (there is no fail-safe if j11 isn't there, just try the default and see)
suitable_java="java"
if ! is_j11 ${suitable_java} ; then
    declare -a other_javas
    other_javas=($(find /usr/ -type f -name java 2> /dev/null | tr '\n' ' '))
    log "Found #${#other_javas[@]} other javas: ${other_javas[@]}"
    for test_java in "${other_javas[@]}"; do
        # log "Test ${test_java}: $(is_j11 ${test_java}; echo $?)" 
        if is_j11 $test_java; then
            suitable_java=$test_java
            break
        fi
    done
fi
log "Using java: $suitable_java"
log "$(${suitable_java} -version)"


clientdir="$( dirname ${BASH_SOURCE[0]} )"
log 'Bundle processing...'
"${suitable_java}" -Dfile.encoding="UTF-8" -cp ${clientdir}/lib/\* de.sekmi.histream.etl.ExportFHIR $*
log 'Bundle processing ... DONE'
