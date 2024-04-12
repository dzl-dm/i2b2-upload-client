#!/bin/bash

## Put everything we need for a git-for-windows client into a zip archive

## TODO: Convert README.md to html (and pdf?) for ease of reading
## Include java and python components
## Include "installer" script - add pip requirements and check pre-requisites
## Include scripts for local processing and DWH processing

## Copy from other parts of the project
mkdir -p bash-client/format/lib
cp -a docker/process_data.sh bash-client/format/fhir-from-datasource.sh
cp -a resources/lib bash-client/format/
mkdir -p bash-client/pseudonym/{src,resources}
cp -a src/process-pid.py bash-client/pseudonym/src/pseudonym-pid-fhir.py
cp -a src/requirements.txt bash-client/pseudonym/src/
cp -a resources/fhir_both-python.xslt bash-client/pseudonym/resources/

## Build the archive
zip -r bash-client.zip bash-client/

## Remove copied file
rm -rf bash-client/format
rm -rf bash-client/pseudonym
