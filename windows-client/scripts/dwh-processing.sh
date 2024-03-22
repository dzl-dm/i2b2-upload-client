#!/bin/bash
## Guide user through options to upload, view, process and delete data from the DWH

df="%Y-%m-%d %H:%M:%S"
function log_debug { [[ "${log_verbosity}" -ge 3 ]] && >&2 echo "[$(date +"$df")] DEBUG: ${@}"; }
function log_info { [[ "${log_verbosity}" -ge 2 ]] && >&2 echo "[$(date +"$df")] INFO: ${@}"; }
function log_warn { [[ "${log_verbosity}" -ge 1 ]] && >&2 echo "[$(date +"$df")] WARN: ${@}"; }
function log_error { >&2 echo "[$(date +"$df")] ERROR: ${@}"; }
>&2 echo "(stderr) logging verbosity set to: ${log_verbosity}"

if ! curl --version > /dev/null 2>&1 ; then
    log_error "cURL not available"
    exit 1
fi
curl_args="-s"
if [[ "${log_verbosity}" -ge 3 ]] ; then
    curl_args="-v"
fi


function api_options {
    ## Ask user what they want from the API, then call the relevant function (or command, if simple enough) to perform the action
    api_options=("List sources known to DWH" "Query specific DWH source" "Push new data to DWH" "Process uploaded data" "Delete a specific DWH dataset")
    select opt in "${api_options[@]}" exit; do
        ## Use option indicies so code looks neater
        case $REPLY in
                1) curl ${curl_args} -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource | jq ;;
                2) query_dwh_source ;;
                3) upload_source ;;
                4) process_dwh_source ;;
                5) delete_dwh_source ;;
                $((${#api_options[@]}+1))) echo "exiting"
                    break 2 ;;
                *) echo Unrecognised choice: $REPLY ;;
        esac
    done
}

function ask_remote_source_name {
    ## Ask user for remote DWH source name (can't verify as it could be for uploading a new source)
    dwh_sources=($(list_dwh_source_names))
    select opt in "${dwh_sources[@]}" New Cancel; do
        ## REPLY is the index chosen
        log_debug "opt: ${opt} (REPLY: ${REPLY} / ${#dwh_sources[@]})"
        case 1 in
                $((REPLY > 0 && REPLY <= ${#dwh_sources[@]}))) echo $opt && return 0 ;;
                $((REPLY == ${#dwh_sources[@]}+1))) ask_new_source_name && return $? ;;
                $((REPLY == ${#dwh_sources[@]}+2))) echo "" && return 1 ;;
                *) echo Unrecognised choice: $REPLY ;;
        esac
        # if [[ $REPLY -eq ${#dwh_sources[@]} ]] ; then
        #     echo "exiting"
        #     return 1
        # elif [[ $REPLY -lt ${#dwh_sources[@]} ]] ; then
        #     echo ${opt}
        #     return 0
        # else
        #     echo "Unrecognised choice: $REPLY"
        # fi
    done
    return 1
}
function ask_new_source_name {
    ## Ask user for a new remote DWH source name
    while true; do
        read -p "Please provide a source name: " sn
        ## Do some sort of sanity checks on name
        if [[ $sn =~ ^[A-Za-z][A-Za-z0-9_]* ]] ; then
            log_debug "Source name ($sn) looks safe..."
            echo "${sn}"
            return 0
        else
            echo "Sorry, this name isn't valid, please try again: '${sn}'" >&2
            # return 1
        fi
    done
}
function ask_local_source_path {
    ## Ask user for the path to a local DWH-ready datasource fhir-bundle
    while true; do
        read -p "Please provide the path to the fhir-bundle xml file you wish to upload: " sp
        ## Check the file exists
        if [[ -f "$sp" ]] ; then
            log_debug "Using file which exists: ($sp)"
            echo "${sp}"
            return 0
        else
            echo "Sorry, this file doesn't exists: '${sp}'\nPlease check the path and try again."
            break
        fi
    done
}

function list_dwh_source_names {
    ## Convert the response into a plain list
    ## Return empty list and error code if curl errors
    if ! curl -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource > /dev/null 2>&1 ; then
        log_warn "Talking to DWH API (${DWH_API_ENDPOINT%/}) failed..."
        echo ""
        return 1
    fi
    ## Convert the json response into list of source_id's 
    source_names=$(curl -s -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource | jq '.[] | .source_id' | tr -d \")
    # log_debug "DWH datasource names: ${source_names}"
    echo ${source_names}
    return 0
}

function query_dwh_source {
    ## Default show status for source, then prompt for info or error
    echo "Please choose the number corresponding to your source: "
    if ! source_name=$(ask_remote_source_name) ; then
        log_error "Source name returned an error..."
        return 1
    fi
    curl ${curl_args} -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl | jq
    api_get_source_options=("Get info" "Get error")
    select opt in "${api_get_source_options[@]}" exit; do 
        ## Use option indicies so code looks neater
        case $REPLY in
                1) curl ${curl_args} -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl/info ;;
                2) curl ${curl_args} -X GET -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${source_name}/etl/error ;;
                $((${#api_get_source_options[@]}+1))) echo "exiting"
                    break 2;;
                *) echo Unrecognised choice: $REPLY ;;
        esac
    done
}

function upload_source {
    ## PUT a local, pseudonymised fhir bundle to the server
    dwh_bundle_path=$(ask_local_source_path)
    # remote_source_name=$(ask_remote_source_name)
    echo "Please choose the number corresponding to your source: "
    if ! remote_source_name=$(ask_remote_source_name) ; then
        log_error "Source name returned an error..."
        return 1
    fi
    if curl ${curl_args} -X PUT -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name}/fhir-bundle -F "fhir_bundle=@${dwh_bundle_path}" ; then
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
}

function process_dwh_source {
    ## Request processing of a DWH datasource via the POST endpoint
    # remote_source_name=$(ask_source_name "Please provide the DWH datasource name you wish to be processed")
    echo "Please choose the number corresponding to your source: "
    if ! remote_source_name=$(ask_remote_source_name) ; then
        log_error "Source name returned an error..."
        return 1
    fi
    if curl ${curl_args} -X POST -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name}/etl ; then
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
    # remote_source_name=$(ask_source_name "Please provide the DWH datasource name you wish to be deleted")
    echo "Please choose the number corresponding to your source: "
    if ! remote_source_name=$(ask_remote_source_name) ; then
        log_error "Source name returned an error..."
        return 1
    fi
    if curl ${curl_args} -X DELETE -H "x-api-key: ${dwh_api_key}" ${DWH_API_ENDPOINT%/}/datasource/${remote_source_name} ; then
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
log_info "Starting script"
api_options
log_info "Script complete"
