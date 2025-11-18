#!/usr/bin/env python3
"""
Description: Communicate with the API endpoint to allow viewing, (re-)uploading and deleting data
stderr: for logs
"""

## Import built-ins
from functools import cache
import json
import os
import sys

## Import third party libraries
import importlib.metadata
import logging
from pydantic_settings import BaseSettings
import requests

class AppMeta():
    """ Purely constants """
    app_name: str = "i2b2-upload-client"
    app_sub_name: str = "DWH client - API processing"
    app_description: str = "Can be used as script or module. Allows all API interactions."

## ---------------- ##
## Create  settings ##
## ---------------- ##
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    DWH_API_ENDPOINT: str = "https://data.dzl.de/api"
    dwh_api_key: str = ""
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(AppMeta.app_sub_name)
logger.setLevel(settings.log_level)
logger.debug("Logging loaded with default configuration")

@cache
def checkApiUserConnection(apiEndpoint:str = None, apiKey:str = None) -> dict:
    """ Connect to API and check for 401 response code
    return {isAuthorized: bool, responseCode: int} 
    """
    ## Pick up defaults here, in case they are changed after loading the module
    if apiEndpoint is None:
        apiEndpoint = settings.DWH_API_ENDPOINT
    if apiKey is None:
        apiKey = settings.dwh_api_key
    logger.debug("Connecting to api: %s", apiEndpoint)
    isAuthorized = False
    response = requests.get(f'{apiEndpoint.rstrip("/")}/datasource', headers={'x-api-key': apiKey})
    logger.debug("Response (%s): %s", response.status_code, response)
    if response.status_code != 401:
        isAuthorized = True
    return {"isAuthorized": isAuthorized, "responseCode": response.status_code}

def isValidApiUser(apiUserCheck:dict = None) -> bool:
    """ Use response from checkApiUserConnection to check for validity """
    if apiUserCheck is None:
        apiUserCheck = checkApiUserConnection()
    if apiUserCheck['isAuthorized'] and apiUserCheck['responseCode'] not in [403]:
        return True
    else:
        logger.error("API connection not valid.")
        return False

def listDwhSources() -> list:
    """ Convert the response into a plain list """
    ## Return empty list if no sources on server (but connection succeeded)
    ## and None if curl/connection errors
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.get(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource', headers={'x-api-key': settings.dwh_api_key})
    logger.debug("Response (%s): %s", response.status_code, response)
    if response.status_code != 200:
        logger.warning("Failed to connect to API")
        return None
    sources = response.json()
    logger.debug("...and data: %s", sources)
    sourceIds = []
    if len(sources) > 0:
        sourceIds = [source['source_id'] for source in sources]
    return sourceIds

def sourceStatus(source_id: str) -> dict:
    """ Convert the response into a plain dict """
    ## Return empty list and error code if curl errors
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.get(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/etl', headers={'x-api-key': settings.dwh_api_key})
    logger.debug("Response: %s", response)
    if response.status_code != 200:
        logger.warning("Failed to connect to API")
        return None
    source = response.json()
    logger.debug("...and data: %s", source)
    return source
def getSourceInfo(source_id: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.get(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/etl/info', headers={'x-api-key': settings.dwh_api_key})
    return response.content.decode()
def getSourceError(source_id: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.get(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/etl/error', headers={'x-api-key': settings.dwh_api_key})
    return response.content.decode()

def deleteSource(source_id: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.delete(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}', headers={'x-api-key': settings.dwh_api_key})
    if response.status_code == 202:
        return "Accepted request, processing...\nPlease refresh status to check progress"
    else:
        return f"Error: Something unexpected happended: {response.status_code}: {response.content}"

def uploadSource(source_id: str, sourceFhirBundlePath: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    url = f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/fhir-bundle'
    ## basic file check
    if not sourceFhirBundlePath or not os.path.isfile(sourceFhirBundlePath):
        return f"Failed to locate file: '{sourceFhirBundlePath}'"
    files = {'fhir_bundle': open(sourceFhirBundlePath, 'rb')}
    headers = {'x-api-key': settings.dwh_api_key}
    response = requests.put(url, files=files, headers=headers)
    if response.status_code == 204:
        return "Uploading...\nPlease refresh status to check progress (If this is a new source, refresh list first with the API connect button)"
    else:
        return f"Error: Something unexpected happedned: {response.status_code}: {response.content}"

def processSource(source_id: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.post(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/etl', headers={'x-api-key': settings.dwh_api_key})
    if response.status_code == 202:
        return "Accepted request, processing...\nPlease refresh status to check progress"
    else:
        return f"Error: Something unexpected happedned: {response.status_code}: {response.content}"

## CLI action processing
def cliSummary():
    """ Render the summary/list of sources the DWH knows of """
    logger.debug("Starting action...")
    sourceIds = listDwhSources()
    print("List of your sources known to the DWH...")
    if len(sourceIds) == 0:
        print("No sources available, try uploading a new source first!")
    else:
        for sourceId in sourceIds:
            print(f'> {sourceId}')
        print("You can use these source names to make further queries and updates")
    print("")

def cliStatus(datasourceName:str):
    """ Provide the status and last update/ativity dates """
    logger.debug("Starting action...")
    sourceDetails = sourceStatus(datasourceName)

    headers = []
    values = []
    for key in sourceDetails:
        head = key
        value = ""
        if type(sourceDetails[key]) == type({}):
            for key2 in sourceDetails[key]:
                head += "/" + key2
                value = sourceDetails[key][key2]
                headers.append(head)
                values.append(value)
        else:
            value = sourceDetails[key]
            headers.append(head)
            values.append(value)
    myTable = PrettyTable(headers)

    myTable.add_row(values)
    print(myTable)
    print("")
def cliInfo(datasourceName:str):
    """ Print info of last update of the datasource """
    logger.debug("Starting action...")
    sourceInfo = getSourceInfo(datasourceName)
    print("Information logged by the server:")
    print(sourceInfo)
    print("")
def cliError(datasourceName:str):
    """ Print server logged errors for the datasource """
    logger.debug("Starting action...")
    sourceError = getSourceError(datasourceName)
    print("Errors logged by the server:")
    print(sourceError)
    print("")

def cliUpload(datasourceName:str, uploadFilepath:str):
    """ Upload a file with fhir bundle data """
    logger.debug("Starting action...")
    print(f"Uploading source: '{datasourceName}'")
    apiResponse = uploadSource(datasourceName, uploadFilepath)
    print(f"Response from server: {apiResponse}")
    time.sleep(2)
    cliStatus(datasourceName)

def cliProcess(datasourceName:str):
    """ Process a file which has already been uploaded """
    logger.debug("Starting action...")
    if datasourceName not in listDwhSources():
        logger.error("Remote source '%s' not recognised, aborting")
        sys.exit(2)
    print(f"About to process source: '{datasourceName}'")
    print("This means the file upload will be added to the DWH database")
    if args.yes >= 1 or areYouSure():
        print(f"Processing source: '{datasourceName}'")
        apiResponse = processSource(datasourceName)
        logger.info("Source processed: '%s'", datasourceName)
        print(f"Response from server: {apiResponse}")
        time.sleep(2)
        cliStatus(datasourceName)
        print("You may need to wait for processing and check the status later.")
        return True
    print("Aborting processing, no action taken")
    return False
def cliDelete(datasourceName:str):
    """ Delete source and show status after a few seconds """
    logger.debug("Starting action...")
    if datasourceName not in listDwhSources():
        logger.error("Remote source '%s' not recognised, aborting")
        sys.exit(2)
    print(f"About to delete source: '{datasourceName}'")
    if args.yes >= 2 or areYouSure():
        print(f"Deleting source: '{datasourceName}'")
        apiResponse = deleteSource(datasourceName)
        logger.info("Source deleted: '%s'", datasourceName)
        print(f"Response from server: {apiResponse}")
        time.sleep(2)
        cliStatus(datasourceName)
        print("You may need to wait for processing and check the status later.")
        return True
    print("Aborting delete, no action taken")
    return False

def areYouSure():
    """ Ask user to confirm action """
    response = input("Please confirm [y/N]:")
    if response.lower() == 'y' or response.lower() == 'yes':
        return True
    return False
def askApiKey():
    """ Ask user to supply API key interactively """
    import getpass
    while True:
        apiKey = getpass.getpass("Enter API key:")
        if len(apiKey) > 4:
            break
        logger.debug("API key should be quite a long string, please try again!")
    return apiKey

## When called as script (not run if imported as module):
if __name__ == "__main__":
    ## Application logic starts here; allow direct processing from CLI using functions unchanged from module use
    import argparse
    from prettytable import PrettyTable
    import time
    logger.info("Starting api processing...")
    logger.warning("WORK IN PROGRESS")
    ## TODO: 
    ## Argparse to determine what the user wants to do (and allow non-sensitive configuration)
    ## Ask user for API endpoint and key if they are defaults
    ## Call relevant function
        ## Potentially print json response nicely

    ## Setup argument processing
    parser = argparse.ArgumentParser(prog=AppMeta.app_name, description=AppMeta.app_description)
    parser.add_argument('--version', action='version', version=AppMeta.app_name)
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity (multiple allowed).')
    parser.add_argument('-y', '--yes', action='count', default=0, help='Assume yes. Don\'t prompt for action confirmations (1x allow updates, 2x allow removal)')
    ## Application specific parameters
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('-l', '-S', '--list', '--summary', action='store_true', help='Fetch summary list of sources from the DWH.')
    action.add_argument('-s', '--status', action='store_true', help='Show status of uploaded datasource.')
    action.add_argument('-i', '--info', action='store_true', help='Show info about the most recently uploaded datasource.')
    action.add_argument('-e', '--error', action='store_true', help='Show error (if exists) about the most recently uploaded datasource.')
    action.add_argument('-u', '--upload', action='store_true', help='Send a new/updated fhir-bundle for a datasource.')
    action.add_argument('-p', '--process', action='store_true', help='Process an uploaded fhir-bundle file data into the DWH database.')
    action.add_argument('-d', '--delete', action='store_true', help='Remove a datasource from the DWH.')

    parser.add_argument('-n', '--ds-name', required=False, help='Name of datasource.')
    parser.add_argument('-f', '--upload-file', required=False, help='Filename for the fhir-bundle.')
    parser.add_argument('-a', '--dwh_api_endpoint', required=False, help='API endpoint for the DWH.')
    args = parser.parse_args()

    ## Map verbose count to log level
    if args.verbose is not None:
        verboseLevels = {1: 'WARNING', 2: 'INFO', 3: 'DEBUG'}
        logger.debug("level set to (verbose = %s - %s): %s", args.verbose, verboseLevels.get(args.verbose, 'DEBUG'), logger.getEffectiveLevel())
        logger.setLevel(verboseLevels.get(args.verbose, 'DEBUG'))
        logger.debug("level set to: %s", logger.getEffectiveLevel())
    logger.debug("args namespace: %s", args)

    ## Check api and key
    count = 0
    while (apiConnection := checkApiUserConnection(apiKey = settings.dwh_api_key))['isAuthorized'] == False:
        if count == 3:
            logger.error("Too many API connection failures, exiting")
            print("Cannot connect to API. Please check the endpoint and key are entered correctly and that the server is running...")
            sys.exit(1)
        count += 1
        settings.dwh_api_key = askApiKey()
    if not isValidApiUser():
        logger.error("Authenticated, but user not valid (%s)", apiConnection['responseCode'])
        print(f"Authenticated, but user not valid. Contact DZL central Data Management for assistance (error code: {apiConnection['responseCode']})...")
        sys.exit(1)

    ## Check args for action and complimenting name/file
    if not any(vars(args).values()):
        logger.warning("You must specify an action (try --help).")
        parser.print_help()
    actions = {'list': 'cliSummary', 'status': 'cliStatus', 'info': 'cliInfo', 'error': 'cliError', 'upload': 'cliUpload', 'process': 'cliProcess', 'delete': 'cliDelete'}
    action = [x for x in actions.keys() if getattr(args, x)][0]
    logger.debug("action: %s", action)
    if action == 'list':
        locals()[actions[action]]()
    elif action in ['status', 'info', 'error', 'process', 'delete']:
        locals()[actions[action]](args.ds_name)
    else:
        locals()[actions[action]](args.ds_name, args.upload_file)
    logger.info("Script run completed!")
