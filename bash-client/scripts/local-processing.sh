#!/bin/bash
## Run the local processing (datasource.xml to fhir and pseudonymisation)

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

## See if the user wants to restrict to -s (single-stage) "f" (fhir) or "p" (pseudonym) processing
single_stage=
SOPTS="s:"
TMP=$(getopt -o "$SOPTS" -n "$CMD" -- "$@") || exit 1
eval set -- "$TMP"
unset TMP
while true; do
    case "$1" in
        -s)
            single_stage="$2"
            shift
            ;;
        --)                                       # end of options
            shift
            break
            ;;
    esac
    shift
done
if [[ $# != 1 ]] ; then
    log_error "You must provide exactly 1 argument, the path to the 'datasource.xml' file"
    exit 1
fi
## Check secret_key variable - disallow default "ChangeMe" and prompt if missing/empty
if [[ ! -n $secret_key || $secret_key = "ChangeMe" ]] ; then
    log_info "secret_key is default or not set, prompting for user input..."
    while true; do
        read -p "Please enter your secret_key: " secret_key_in
        ## Do some sort of sanity checks on key
        if [[ "$secret_key_in" =~ ^[A-Za-z][A-Za-z0-9\`\&\;\'\<\>_#$%@^~*+!?=.,:-]*$ ]] ; then
            secret_key=$secret_key_in
            break
        else
            echo "Sorry, this name isn't valid, please try again..." >&2
        fi
    done
fi

## Set the datasource_path and _dir for both processing parts to use
rel_datasource_path=$1
datasource_path=$(echo "$(cd "$(dirname "${rel_datasource_path}")"; pwd)/$(basename "${rel_datasource_path}")")
[[ -f "${datasource_path}" ]] || (log_error "Provided parameter (${datasource_path}) is not a file on this filesystem, aborting..." && exit 1)
datasource_dir=$( dirname "${datasource_path}" )
log_debug "abs_datasource_path: ${abs_datasource_path} - datasource_path: ${datasource_path} - datasource_dir: ${datasource_dir}"

function datasource_to_fhir {
    ## Prepare the source data into a pseudonymised fhir-bundle
    [[ -f ${datasource_path} ]] || (echo "File doesn't exist! ${datasource_path}" && exit 1)
    log_info "Processing a specific source (${datasource_path})..."
    log_debug "Checking dir is ready: ${datasource_dir}"
    [[ -d ${datasource_dir}/client-output ]] && rm ${datasource_dir}/client-output/* || mkdir "${datasource_dir}/client-output/"
    raw_fhir_path=${datasource_dir}/client-output/fhir-bundle-raw.xml
    log_debug "Directories and paths set, processing... (${client_basedir}/format/fhir-from-datasource.sh ${datasource_path})"
    ${client_basedir}/format/fhir-from-datasource.sh ${datasource_path} > ${raw_fhir_path}
    log_info "Data now in fhir-bundle format: ${raw_fhir_path}"
}

function pseudonymise_fhir {
    ## Pseudonymise the fhir-bundle without changing any other data
    log_debug "Start pseudonymisation..."
    ## The python pseudonymisation script uses env vars for settings
    export input_fn=${datasource_dir}/client-output/fhir-bundle-raw.xml
    export output_fn=${datasource_dir}/client-output/fhir-bundle-dwh.xml
    export secret_key=${secret_key}
    ${client_basedir}/pseudonym/src/pseudonym-pid-fhir.py
    log_info "Pseudonym processing complete, see DWH-ready output at: (${output_fn})..."
}

## START
if [[ ${single_stage} = "f" ]] ; then
    datasource_to_fhir
elif [[ ${single_stage} = "p" ]] ; then
    pseudonymise_fhir
else
    datasource_to_fhir
    pseudonymise_fhir
fi
## END

## Cleanup venv...
[[ -d "${client_basedir}/.venv" ]] && deactivate
