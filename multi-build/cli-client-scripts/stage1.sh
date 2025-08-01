#!/usr/bin/env bash
## Process data into fhir format

df="%Y-%m-%d %H:%M:%S"
script_name="$(basename ${BASH_SOURCE[0]})"
function log { >&2 echo "[$(date +"$df")] {${script_name}} DEBUG: ${@}"; }

## Check java is available
java -version > /dev/null 2>&1 || (log "Java not available" && exit 1)

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


clientdir="$( dirname ${BASH_SOURCE[0]} )"
CLASSPATH=""
for jar in $(ls -1d ${clientdir}/lib/*); do
	CLASSPATH=$jar:$CLASSPATH
done

log 'Bundle processing...'
"${suitable_java}" -Dfile.encoding="UTF-8" -cp ${CLASSPATH} de.sekmi.histream.etl.ExportFHIR $*
log 'Bundle processing ... DONE'

