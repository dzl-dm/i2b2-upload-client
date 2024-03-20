#!/usr/bin/env bash

## coordinate the processing:
    # * SHELL: Scan data volume for new datasources to process (output to: fhir-bundle-{raw,dwh}.xml)
	# * JAVA: csv + xml config -> xml fhir bundle
	# * PYTHON: xml fhir bundle -> pseudonymised xml fhir bundle
## Offer user what to do with the data or only query the DWH
	# * cURL: xml fhir bundle -> DWH server

df="%Y-%m-%d %H:%M:%S"
function log_debug { [[ "${log_verbosity}" -ge 3 ]] && >&2 echo "[$(date +"$df")] DEBUG: ${@}"; }
function log_info { [[ "${log_verbosity}" -ge 2 ]] && >&2 echo "[$(date +"$df")] INFO: ${@}"; }
function log_warn { [[ "${log_verbosity}" -ge 1 ]] && >&2 echo "[$(date +"$df")] WARN: ${@}"; }
function log_error { >&2 echo "[$(date +"$df")] ERROR: ${@}"; }
>&2 echo "(stderr) logging verbosity set to: ${log_verbosity}"
case $log_verbosity in
    0) export log_level=ERROR ;;
    1) export log_level=WARNING ;;
    2) export log_level=INFO ;;
    3) export log_level=DEBUG ;;
esac

## Scan /datasources/ which is a mounted directory of the users local datasources
## For each source, check if there are output files and compare the dates to the config and source files
function scan_sources {
    # for dir in /datasources/*/; do
    for dir in $(ls -1 /datasources/); do
        if [ ! -d ${dir}/client-output ] ; then
            echo "Source '${dir}' has not yet been processed"
        else
            echo "Source '${dir}' is also available"
            ## TODO: Check dates...
            ## Check modify dates of source files (datasource.xml and any <url> references inside it)
            # source_date=
            # output_date
            # echo "Source '${dir}' was last updated on '' and last processed on ''"
        fi
    done
}

## Ask user if they want to process only 1 specific source, auto process all or skip to the API interaction
function initial_options {
    base_options=("Scan and process available local sources" "Process specific source" "Skip to API interaction options")
    select opt in "${base_options[@]}" exit; do
    ## Use option indicies so code looks neater
    case $REPLY in
            1) echo "Sorry, this function is not yet implemented!" ;;
            2) process_source ;;
            3) api_options ;;
            $((${#base_options[@]}+1))) echo "exiting"
                break 2;;
            *) echo Unrecognised choice: $REPLY ;;
    esac
    done
}

## For any source being checked
    ## If source or config is newer than output (or output doesn't exist), (re-)process

    ## If there is an error, tell user with which source and try to add details
function process_source {
    log_debug "Processing a specific source..."
    read -p 'Please provide a source name (the directory name): ' sn
        if [[ "$(cd /datasources && echo */ )" =~ "${sn}/" ]] ; then
        echo "Source exists ($sn)! Processing..."
        cd /datasources/${sn}
        mkdir -p client-output
        rm client-output/*
        /upload-client/fhir-transform/process_data.sh datasource.xml > client-output/fhir-bundle-raw.xml
        export input_fn=client-output/fhir-bundle-raw.xml
        export output_fn=client-output/fhir-bundle-dwh.xml
        /upload-client/pseudonym/src/process-pid.py
        return 0
    else
        echo "Dir not found: $sn"
        return 1
    fi
}

## Once all sources are processed (or skipped), present API interaction options (check sources, upload new, etc)
function api_options {
    api_options=("List sources known to DWH" "Query specific source" "Push new data" "Delete data")
    select opt in "${api_options[@]}" exit; do 
    ## Use option indicies so code looks neater
    case $REPLY in
            1) break ;;
            2) break ;;
            3) break ;;
            4) break ;;
            $((${#api_options[@]}+1))) echo "exiting"
                break 2;;
            *) echo Unrecognised choice: $REPLY ;;
    esac
    done
}


## Start logic
scan_sources
initial_options
exit 0
