#!/usr/bin/env python3
"""
Description: Communicate with the API endpoint to allow viewing, (re-)uploading and deleting data
stderr: for logs
"""

## library imports
import json
import logging
import os
from pydantic_settings import BaseSettings
import requests
import sys

## ---------------- ##
## Create  settings ##
## ---------------- ##
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    app_name: str = "DWH fhir-bundle patient pseudonymization"
    app_description: str = "Pseudonymize patients in an xml fhir-bundle"
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    DWH_API_ENDPOINT: str = "http://localhost/api"
    dwh_api_key: str = "ChangeMe"
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(settings.app_name)
logger.setLevel(settings.log_level)
logger.warning("Logging loaded with default configuration")

def listDwhSources() -> list:
    """ Convert the response into a plain list """
    ## Return empty list and error code if curl errors
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.get(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource', headers={'x-api-key': settings.dwh_api_key})
    logger.debug("Response: %s", response)
    if response.status_code != 200:
        logger.warning("Failed to connect to API")
        return None
    sources = response.json()
    logger.debug("...and data: %s", sources)
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
        return f"Error: Something unexpected happedned: {response.status_code: response.content}"

def uploadSource(source_id: str, sourceFhirBundlePath: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    url = f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/fhir-bundle'
    files = {'file': ('fhir_bundle', open(sourceFhirBundlePath, 'rb'))}
    headers = {'x-api-key': settings.dwh_api_key}
    response = requests.put(url, files=files, headers=headers)
    if response.status_code == 204:
        return "Uploading...\nPlease refresh status to check progress (If this is a new source, refresh list first with the API connect button)"
    else:
        return f"Error: Something unexpected happedned: {response.status_code: response.content}"

def processSource(source_id: str) -> str:
    """ Call endpoint """
    logger.debug("Connecting to api: %s", settings.DWH_API_ENDPOINT)
    response = requests.post(f'{settings.DWH_API_ENDPOINT.rstrip("/")}/datasource/{source_id}/etl', headers={'x-api-key': settings.dwh_api_key})
    if response.status_code == 202:
        return "Accepted request, processing...\nPlease refresh status to check progress"
    else:
        return f"Error: Something unexpected happedned: {response.status_code: response.content}"

## When called as script (not run if imported as module):
if __name__ == "__main__":
    ## Application logic starts here; processing steps abstracting complexity into functions
    logger.info("Starting api processing...")
    logger.warning("NOT IMPLEMENTED")

    logger.info("Script run completed!")
