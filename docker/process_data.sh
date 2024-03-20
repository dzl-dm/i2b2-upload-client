#!/usr/bin/env bash
## Process data into fhir format

df="%Y-%m-%d %H:%M:%S"
function log { >&2 echo "[$(date +"$df")] DEBUG: ${@}"; }

clientdir=$( dirname "${BASH_SOURCE[0]}" )
java -version
log 'Bundle processing...'
java -Dfile.encoding="UTF-8" -cp ${clientdir}/lib/\* de.sekmi.histream.etl.ExportFHIR $*
log 'Bundle processing ... DONE'
