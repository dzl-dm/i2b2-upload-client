#!/bin/bash

df="%Y-%m-%d %H:%M:%S"
function log_debug { [[ "${log_verbosity}" -ge 3 ]] && >&2 echo "[$(date +"$df")] DEBUG: ${@}"; }
function log_info { [[ "${log_verbosity}" -ge 2 ]] && >&2 echo "[$(date +"$df")] INFO: ${@}"; }
function log_warn { [[ "${log_verbosity}" -ge 1 ]] && >&2 echo "[$(date +"$df")] WARN: ${@}"; }
function log_error { >&2 echo "[$(date +"$df")] ERROR: ${@}"; }
>&2 echo "(stderr) logging verbosity set to: ${log_verbosity}"

## Installer for git on windows/git-bash
[[ java -version > /dev/null 2>&1 ]] || log_error "Java not available" && exit 1
[[ python --version > /dev/null 2>&1 ]] || log_error "Python not available" && exit 1

function datasource_to_fhir {
    ## Prepare the source data into a pseudonymised fhir-bundle
    datasource_path=$1
    [[ -f ${datasource_path} ]] || echo "File doesn't exist! ${datasource_path}" && exit 1
    log_info "Processing a specific source (${datasource_path})..."
    datasource_dir=$( dirname "${datasource_path}" )
    mkdir "${datasource_dir}/client-output/"
    rm ${datasource_dir}/client-output/*
    raw_fhir_path=${datasource_dir}/client-output/fhir-bundle-raw.xml
    fhir-from-datasource.sh ${datasource_path} > ${raw_fhir_path}
    log_debug "Data now in fhir-bundle format: ${raw_fhir_path}"
}

function pseudonymise_fhir {
    ## Pseudonymise the fhir-bundle without changing any other data
    log_debug "Start pseudonymisation..."
    ## The python pseudonymisation script uses env vars for settings
    export input_fn=${datasource_dir}/client-output/fhir-bundle-raw.xml
    export output_fn=${datasource_dir}/client-output/fhir-bundle-dwh.xml
    export secret_key=${datasource_dir}/client-output/fhir-bundle-dwh.xml
    pseudonym-pid-fhir.py
    log_info "Processing complete, see DWH-ready output at: (${output_fn})..."
}

datasource_to_fhir $1
pseudonymise_fhir
