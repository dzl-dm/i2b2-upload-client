#!/bin/bash

## Put everything we need for a git-for-windows client into a zip archive

## TODO: Convert README.md to html (and pdf?) for ease of reading
## Include java and python components
## Include "installer" script - add pip requirements and check pre-requisites
## Include scripts for local processing and DWH processing

## Copy from other parts of the project
mkdir -p windows-client/format/lib
cp -a docker/process_data.sh windows-client/format/fhir-from-datasource.sh
cp -a resources/lib windows-client/format/
mkdir -p windows-client/pseudonym/{src,resources}
cp -a src/process-pid.py windows-client/pseudonym/src/pseudonym-pid-fhir.py
cp -a src/requirements.txt windows-client/pseudonym/src/
cp -a resources/fhir_both-python.xslt windows-client/pseudonym/resources/

## Build the archive
zip -r windows-client.zip windows-client/

## Remove copied file
rm -rf windows-client/format
rm -rf windows-client/pseudonym
