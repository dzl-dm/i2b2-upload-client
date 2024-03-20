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
function scan_local_sources {
    ## Check which local sources are available and when they were updated locally and remotely
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


function initial_options {
    ## Ask user if they want to process only 1 specific source, auto process all or skip to the API interaction
    base_options=("Scan and process available local sources" "Process specific source" "Skip to API interaction options")
    select opt in "${base_options[@]}" exit; do
    ## Use option indicies so code looks neater
    case $REPLY in
            1) echo "Sorry, this function is not yet implemented!" ;;
            2) process_local_source ;;
            3) api_options ;;
            $((${#base_options[@]}+1))) echo "exiting"
                break 2;;
            *) echo Unrecognised choice: $REPLY ;;
    esac
    done
}

function process_local_source {
    ## Prepare the source data into a pseudonymised fhir-bundle
    log_debug "Processing a specific source..."
    read -p 'Please provide a source name (the directory name): ' sn
    if [[ "$(cd /datasources && echo */ )" =~ "${sn}/" && ${sn} != "" ]] ; then
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
    ## Ask user what they want from the API, then call the relevant function (or command, if simple enough) to perform the action
    api_options=("List sources known to DWH" "Query specific DWH source" "Push new data to DWH" "Process uploaded data" "Delete a specific DWH dataset")
    select opt in "${api_options[@]}" exit; do 
        ## Use option indicies so code looks neater
        case $REPLY in
                1) curl -v -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource | jq ;;
                2) query_dwh_source ;;
                3) upload_source ;;
                4) process_dwh_source ;;
                5) delete_dwh_source ;;
                $((${#api_options[@]}+1))) echo "exiting"
                    break 2;;
                *) echo Unrecognised choice: $REPLY ;;
        esac
    done
}

function ask_source_name {
    ## Ask user for remote DWH source name (can't verify as it could be for uploading a new source)
    question_text=${1:-"Please provide a source name"}
    default_answer=$2
    while true; do
        read -p "${question_text}: " sn
        ## Do some sort of sanity checks on name
        # if [[ "$(cd /datasources && echo */ )" =~ "${sn}/" && ${sn} != "" ]] ; then
        if [[ $sn =~ ^[A-Za-z][A-Za-z0-9_]* ]] ; then
            log_debug "Source name ($sn) looks safe..."
            echo "${sn}"
            return 0
        else
            echo "Sorry, this name isn't valid: '${sn}'"
            break
        fi
    done
}

function query_dwh_source {
    ## Default show status for source, then prompt for info or error
    source_name=$(ask_source_name)
    curl -v -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl | jq
    api_get_source_options=("Get info" "Get error")
    select opt in "${api_get_source_options[@]}" exit; do 
        ## Use option indicies so code looks neater
        case $REPLY in
                1) curl -v -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl/info ;;
                2) curl -v -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl/error ;;
                $((${#api_get_source_options[@]}+1))) echo "exiting"
                    break 2;;
                *) echo Unrecognised choice: $REPLY ;;
        esac
    done
}

function upload_source {
    ## PUT a local, pseudonymised fhir bundle to the server
    local_source_name=$(ask_source_name "Please provide which local data source you want to upload (the directory name)")
    remote_source_name=$(ask_source_name "Please provide the datasource name you wish to use in the DWH (could be same as local, or different)" "${local_source_name}")
    if [ -d /datasources/${local_source_name} ] ; then
        dwh_bundle_path="/datasources/${local_source_name}/client-output/fhir-bundle-dwh.xml"
        if [ -d /datasources/${local_source_name}/client-output ] && [ -f "${dwh_bundle_path}" ] ; then
            if curl -v -X PUT -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name}/fhir-bundle -F "fhir_bundle=@${dwh_bundle_path}" ; then
                msg_core="The DWH has accepted new data for '${remote_source_name}' (from '${local_source_name}')."
                msg_full="${msg_core} Please check the status until it changes from 'Uploading' -> 'Uploaded', then you can trigger the processing."
                log_info ${msg_core} 
                echo "${msg_full}"
                return 0
            else
                fail_msg_core="Something went wrong uploading the data to the DWH for '${remote_source_name}' (from '${local_source_name}')."
                fail_msg="${fail_msg_core} Please check your connectivity and contact the DWH maintainer if the problem persists."
                log_warn ${fail_msg_core} 
                echo "${fail_msg}"
                return 1
            fi
        else
            log_warn "Local source not fully processed '${local_source_name}'"
            echo "Local source not fully processed '${local_source_name}'"
            return 1
        fi
    else
        log_warn "Local source not available '${local_source_name}'"
        echo "Local source not available '${local_source_name}'"
        return 1
    fi
}

function process_dwh_source {
    ## Request processing of a DWH datasource via the POST endpoint
    remote_source_name=$(ask_source_name "Please provide the DWH datasource name you wish to be processed")
    if curl -v -X POST -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name}/etl ; then
        msg_core="The DWH has accepted and queued processing of datasource '${remote_source_name}'."
        msg_full="${msg_core} Please check the status until it changes from 'Pending' -> 'Processing' => 'Succeeded' or 'Failed'."
        log_info ${msg_core} 
        echo "${msg_full}"
        return 0
    else
        fail_msg_core="Something went wrong requesting the datasource '${remote_source_name}' to be processed."
        fail_msg="${fail_msg_core} Please check your connectivity and contact the DWH maintainer if the problem persists."
        log_warn ${fail_msg_core} 
        echo "${fail_msg}"
        return 1
    fi
}

function delete_dwh_source {
    ## Request deletion of a DWH datasource
    remote_source_name=$(ask_source_name "Please provide the DWH datasource name you wish to be deleted")
    if curl -v -X DELETE -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name} ; then
        msg_core="The DWH has accepted and queued deletion of datasource '${remote_source_name}'."
        msg_full="${msg_core} Please check the status until it changes from 'Pending' -> 'Deleted'."
        log_info ${msg_core} 
        echo "${msg_full}"
        return 0
    else
        fail_msg_core="Something went wrong requesting the datasource '${remote_source_name}' to be deleted."
        fail_msg="${fail_msg_core} Please check your connectivity and contact the DWH maintainer if the problem persists."
        log_warn ${fail_msg_core} 
        echo "${fail_msg}"
        return 1
    fi
}

## Start logic
scan_local_sources
initial_options
exit 0
