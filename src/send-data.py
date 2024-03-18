#!/usr/bin/env python3
"""
Description: Testing sending processed data to a remote server over SSH (or later WebDAVS)
"""

## logging imports
import logging
import logging.config
import os
import yaml

## Setup logging (before importing other modules - so we see the logging from them)
if not os.path.isdir("./logs"):
    os.mkdir("./logs")
with open("./configuration/logging.yaml", "r") as f:
    log_config = yaml.load(f, Loader=yaml.FullLoader)
logging.config.dictConfig(log_config)
## Load logger for this file
logger = logging.getLogger(__name__)
logger.debug("Logging loaded and configured")

## 3rd party importsfrom lxml import etree
import hashlib
import io
import resource
import subprocess
import sys
import time


def runx(data_fn='sample-fhir.xml', remote_server="localhost", remote_dest_path="~/dwh-uploads/"):
    """ Call system ssh to send data """
    subprocess.run(["scp", "-C", data_fn, "{}:{}".format(remote_server, remote_dest_path)])

logger.info("START")
# runx(data_filename="sample-fhir-out.xml", remote_server="localhost")
runx(data_fn="sample-fhir-out.xml", remote_server="dzl-dwh.fb11.uni-giessen.de")
logger.info("END")
