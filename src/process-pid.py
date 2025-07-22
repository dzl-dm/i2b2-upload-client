#!/usr/bin/env python3

"""
    Script to pseudonymize an xml fhir-bundle
"""

## ---------------- ##
## Create  settings ##
## ---------------- ##
import os
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    xslt_fn:str = f"{os.path.abspath(os.path.dirname(__file__))}/../resources/fhir_both-python.xslt"
    secret_key: str
    input_fn: str
    output_fn: str

settings = Settings()

import logging
## Format the root logger
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)

logger.debug("settings and logging loaded and configured")
logger.debug("Settings: %s", settings)

## 3rd party imports
import hashlib
from lxml import etree
import sys

## For each invocation of the application, we create a dict of patients and list their encounters
patient_encounters:dict[str, list] = {}

def _transform_xml_ids(doc, format='fhir'):
    """ Use XSLT to edit the id attributes in patient and encounter tags
    FunctionNamespace is used to access python function(s) providing the logic for setting the id
    """
    ns = etree.FunctionNamespace("CustomXSLTfns")
    ns['_hash_ids'] = _hash_ids
    ns['_compute_encounter_id'] = _compute_encounter_id

    # xslt_doc = etree.ElementTree(etree.fromstring(xslt))
    if format == 'fhir':
        xslt_doc = etree.parse(settings.xslt_fn)
    elif format == 'custom':
        xslt_doc = etree.parse("xslt/oldFormat_both.xslt")
        # xslt_doc = etree.parse("xslt/oldFormat_pid.xslt")
    else:
        logger.error("Unrecognised format: %s", format)
        exit(1)
    transform = etree.XSLT(xslt_doc)
    doc = transform(doc)
    return doc

def _hash_ids(context, given_name:str, surname:str, birthdate:str, salt:str = settings.secret_key) -> str:
    """ Hash the combination of:
        * salt
        * given-name
        * surname
        * birthdate
        with the local secret-key as the salt
        :param: "context" is required for XSLT to call the function
    """
    # logger.debug("Creating user pseudonym...")
    return hashlib.sha3_256(
        "{salt}|{given_name}|{surname}|{birthdate}".format(
            salt=salt.encode('UTF-8'),
            given_name=given_name,
            surname=surname,
            birthdate=birthdate
            ).encode('UTF-8')
        ).hexdigest()

def _compute_encounter_id(context, pid:str, eid:str) -> str:
    """ Increment the encounter id for this patient 
    Zero indexed list
    """
    ## Store a list of encounter ID's for each patient, appending as you find them, return the list position for the id
    logger.debug("Patient id: %s ++ Encounter ID: %s", pid, eid)
    if pid not in patient_encounters:
        ## Add patient and encounter id
        patient_encounters[pid] = [eid]
        ## Default start eid of 0
        return "0"
    if eid not in patient_encounters[pid]:
        ## Add encounter id
        patient_encounters[pid].append(eid)
        ## Return length of eid list -1
        return len(patient_encounters[pid]) - 1
    ## Otherwise, we've already seen it, just find it and return the position
    return patient_encounters[pid].index(eid)

def runx(salt, in_fn='sample-fhir.xml', out_fn='sample-fhir-out.xml', format='fhir'):
    """ Run using XSLT to do the heavy lifting """
    if not salt:
        logger.error("Secret key/salt must be set! Please run the application again with a key.")
        sys.exit(1)
    logger.info("Transforming XML with XSLT...")
    in_tree = etree.parse(in_fn)
    out_tree = _transform_xml_ids(in_tree, format)
    # logger.debug("out_tree: %s", out_tree)
    ## TODO: TOFIX: Encoding bug str not compatible with xml_declaration
    with open(out_fn, 'w') as out_fh:
        ## Writing xml declaration isn't compatible with str encoding?!
        out_fh.write('<?xml version="1.0" ?>\n' + etree.tostring(
                                    out_tree,
                                    pretty_print=True,
                                    xml_declaration=False,
                                    encoding=str,
                                    standalone=out_tree.docinfo.standalone
                                    ))

if __name__ == "__main__":
    logger.info("START")
    runx(salt = settings.secret_key, in_fn = settings.input_fn, out_fn = settings.output_fn, format = "fhir")
    logger.info("END")
    sys.exit(0)
