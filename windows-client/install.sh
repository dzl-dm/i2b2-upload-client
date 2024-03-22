#!/bin/bash

## Installer for git on windows/git-bash
## User must have java, python and cURL available
[[ java -version > /dev/null 2>&1 ]] || echo "Java not available" && exit 1
[[ python --version > /dev/null 2>&1 ]] || echo "Python not available" && exit 1
[[ curl --version > /dev/null 2>&1 ]] || echo "cURL not available" && exit 1

## Install python libraries
pip install -r src/requirements.txt

## Add scipts to PATH
export PATH=$PATH:"$( dirname "${BASH[0]}" )/scripts"
