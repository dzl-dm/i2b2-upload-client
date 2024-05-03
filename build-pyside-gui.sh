#!/bin/bash

## Put everything we need for a python (PySide6) GUI client into a zip archive

## Include java and python components
## Include "installer" script - add pip requirements and check pre-requisites
## Include scripts for local processing and DWH processing

## Build parts of the client
mkdir -p gui-client/src
cp -a gui/src/requirements.txt gui-client/src/
cp -a gui/src/dwh_client.py gui-client/src/
cp -a gui/src/mainWindow.ui gui-client/src/
mkdir -p gui-client/resources
cp -a resources/DzlLogoSymmetric.webp gui-client/resources/
cp -a resources/install-gui.sh gui-client/
cp -a resources/dwh_client.sh gui-client/
## Copy from other parts of the project
mkdir -p gui-client/format/lib
cp -a resources/lib gui-client/format/
mkdir -p gui-client/pseudonym
cp -a src/stream-pseudonymization.py gui-client/pseudonym/
mkdir -p gui-client/api
cp -a src/api_processing.py gui-client/api

## Convert the markdown ReadMe to more universal HTML
pandoc -f markdown README.md > gui-client/README.html

## Build the archive
zip -r gui-client.zip gui-client/

## Remove copied files
# rm -rf gui-client
