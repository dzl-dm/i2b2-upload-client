#!/usr/bin/env python3
"""
Description: Pseudonymise an XML fhir bundle by hashing the PID and removing other name related tags
Input: Fhir bundle xml line by line via stdin
Output: fhir bundle xml via std out
stderr: for logs

Usage: cat ./tmp/sample-fhir.xml | src/stream-pseudonymization.py > tmp/sample-fhir-pseudonyms.xml 2>> log/pseudonymisation.log
Explainer: Each entry is loaded into memory in turn, if its a patient, its pseudonymised, then its written
As of 27.11.25, this can be used as a module. It can accept in/out file as opposed to only stdin/out in script mode
"""

## Import built-ins
import csv
import hashlib
import os
import sys
import xml.sax

## Import third party libraries
import logging
import lxml.sax
from pydantic_settings import BaseSettings

## ---------------- ##
## Create  settings ##
## ---------------- ##
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    secret_key: None|str = None
    user_mapping_filename: str = "psn-cache.tsv"
    user_mapping_separator: str = "\t"
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)
logger.warning("Logging loaded with default configuration")

def is_stdin_piped():
    return not os.isatty(0)

class FhirStream(xml.sax.ContentHandler):
    """ SAX ContentHandler to help build each <Entry> by informing an lxml class """
    entryResourceTypes:list[str] = ["Patient", "Encounter"]
    def __init__(self, target, mapping_output: None|csv.DictWriter = None):
        """ Ensure the XML definition is written
        Also setup the monitoring dict to detect clashes
        """
        self.currentEntryResourceType:str = None
        self.currentSubElement = lxml.sax.ElementTreeContentHandler()
        self.currentDepth:int = 0
        self.currentPatient:int = None
        self.currentEncounter:int = None
        self.mapping_output = mapping_output
        self.target = target

        ## Share the xml declaration (to target)
        self.target.send(('init', ('xml', {'version': '1.0'}))) ## '<?xml version="1.0" ?>'

    def startElement(self, name, attrs):
        """ Depending on the element, build up the Entry sub-element in lxml """
        self.currentDepth += 1
        if name == "Bundle":
            self.target.send(('start', ('Bundle', attrs)))
        else:
            if name in self.entryResourceTypes:
                ## Update resource type
                self.currentEntryResourceType = name
            if name == "id":
                if self.currentEntryResourceType == "Patient":
                    self.currentPatient = attrs['value']
                elif self.currentEntryResourceType == "Encounter":
                    self.currentEncounter = attrs['value']
            ## Format attributes as dict which lxml can understand
            attrPairsNS:dict = {}
            for (key, value) in attrs.items(): 
                attrPairsNS[(None, key)] = value
            self.currentSubElement.startElementNS((None, name), name, attrPairsNS)

    def characters(self, cdata):
        """ Future proof in case we have cData in our bundle in the future """
        txt_str = cdata.strip()
        if len(txt_str) > 0:
            self.currentSubElement.characters(cdata)

    def endElement(self, name):
        """ If ending an entry, its time to evaluate if we pseudonymize before writing to stdout """
        self.currentDepth -= 1
        if name == "Bundle":
            self.target.send(('end', 'Bundle'))
        else:
            self.currentSubElement.endElementNS((None, name), name)
            if self.currentDepth == 1:
                if self.currentEntryResourceType == "Patient":
                    #logger.debug("Pseudonymising patient...")
                    self._pseudonymizePatient()
                elif self.currentEntryResourceType == "Encounter":
                    #logger.debug("Using basic sequence for encounter id...")
                    self._cleanEncounterId()
                self._writeCurrentElement()
                #logger.debug('Clearing lxml element "%s"...', name)
                self.currentEntryResourceType = None
                self.currentSubElement = lxml.sax.ElementTreeContentHandler()

    def _writeCurrentElement(self):
        """ Write the sub-element """
        treeXml = lxml.etree.tostring(self.currentSubElement.etree.getroot(), pretty_print=False).decode('UTF-8')
        ## Slightly hacky, we've already constructed a sub-element, so just write it
        self.target.send(('data', treeXml))

    def _cleanEncounterId(self):
        """ Use fhir id as identifier value """
        ##TODO: Should this reset per patient?
        ## Reference elements with xpath; reasonably robust
        if len(self.currentSubElement.etree.xpath("//resource/Encounter/identifier/value")) > 1:
            logger.warning("Encounter element has more than 1 'identifier/value' element (will update only the 1st):\n%s", lxml.etree.tostring(self.currentSubElement.etree.xpath("//resource/Encounter")[0], pretty_print=True).decode('UTF-8'))
        self.currentSubElement.etree.xpath("//resource/Encounter/identifier/value")[0].attrib['value'] = self.currentEncounter

    def _pseudonymizePatient(self):
        """ Hash (with salt) the PID and remove other name information """
        ## Reference elements with xpath
        self.currentSubElement.etree.xpath("//resource/Patient/identifier/value")[0].attrib['value'] = _hash_ids(
            self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/name/given/@value")),
            self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/name/family/@value")),
            self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/birthDate/@value")),
        )
        mapped_patient = {
            "given-names": self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/name/given/@value")),
            "surname": self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/name/family/@value")),
            "birthdate": self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/birthDate/@value")),
            "pseudonym": self._validAttrib(self.currentSubElement.etree.xpath("//resource/Patient/identifier/value/@value")),
        }
        self.mapping_output.writerow(mapped_patient)
        if len(self.currentSubElement.etree.xpath("//resource/Patient/name")) > 1:
            logger.warning("Patient '%s' has more than 1 'name' entry, removing all, 1st occurance used for pseudonymization", self.currentPatient)
        for nameElem in self.currentSubElement.etree.xpath("//resource/Patient/name"):
            self.currentSubElement.etree.xpath("//resource/Patient")[0].remove(nameElem)

    def _validAttrib(self, xpathAttrib) -> str:
        """ Clean up the attribute in case its got multiple or zero elements."""
        if len(xpathAttrib) == 1:
            return xpathAttrib[0]
        elif len(xpathAttrib) > 1:
            logger.warning("There are multiple matching attributes (returning 1st)! '%s'", xpathAttrib)
            return xpathAttrib[0]
        else:
            return ""

def _hash_ids(given_name:str, surname:str, birthdate:str, salt:None|str = None, sep:str = "|") -> str:
    """ Hash the combination of:
        * salt
        * given-name
        * surname
        * birthdate
        with the local secret-key as the salt
    """
    if not salt:
        salt = settings.secret_key
    #logger.debug("Creating user pseudonym...")
    return hashlib.sha3_256(
        "{salt}{sep}{given_name}{sep}{surname}{sep}{birthdate}".format(
            sep=sep,
            salt=salt.encode('UTF-8'),
            given_name=given_name,
            surname=surname,
            birthdate=birthdate
            ).encode('UTF-8')
        ).hexdigest()

def _print_xml_target():
    """ Prints (so stdout) each element/chunk of xml as its received. """
    while True:
        action = yield
        if action is not None:
            print(_xml_snippet_builder(action))

def _write_xml_target(out_file:str):
    """ Writes each element/chunk of xml as its received to a specified file. """
    with open(out_file, 'w', newline='\n') as xml_out:
        while True:
            action = yield
            if action is not None:
                xml_out.write(_xml_snippet_builder(action)+"\n")


def _xml_snippet_builder(action: tuple) -> str:
    """ Convert tuple into XML string. """
    xml_snippet = ""
    # logger.debug("Processing xml action: %s", action)
    if action[0] == 'init':
        attr_text = ', '.join([f'{k}="{v}"' for k,v in action[1][1].items()])
        xml_snippet = f'<?{action[1][0]} {attr_text} ?>'
    elif action[0] == 'start':
        attr_text = ', '.join([f'{k}="{v}"' for k,v in action[1][1].items()])
        xml_snippet = f'<{action[1][0]} {attr_text}>'
    elif action[0] == 'end':
        xml_snippet = f'</{action[1]}>'
    elif action[0] == 'data':
        xml_snippet = action[1]

    return xml_snippet

def process_fhir_bundle(in_file:str, out_file:str, salt:None|str = None):
    """ If not calling as script, use this function. """
    logger.info("Starting fhir pseudonymization...")
    ## TODO: This is hacky
    if salt:
        settings.secret_key = salt
    else:
        if not settings.secret_key:
            logger.error("No secret key set! Cannot continue.")
            return False
    target = _write_xml_target(out_file)
    next(target)  # Prime the generator

    with open(in_file, 'r', newline='\n') as in_f:
        mapping_headings = ["given-names","surname","birthdate","pseudonym"]
        with open(settings.user_mapping_filename, 'w', newline='\n') as map_f:
            mapping_writer = csv.DictWriter(map_f, delimiter=settings.user_mapping_separator, quotechar='"', quoting=csv.QUOTE_MINIMAL, fieldnames=mapping_headings, lineterminator='\n')
            mapping_writer.writeheader()

            ## Set up the sax parser
            sp = xml.sax.make_parser()
            sp.setContentHandler(FhirStream(target = target, mapping_output = mapping_writer))
            sp.setFeature(xml.sax.handler.feature_namespaces, 0)

            ## sax parses by emitting events when a tag or data is found, so the response to the events is all handled in the ContentHandler class above
            sp.parse(in_f)

    logger.info("Module call complete")
    return True

## When called as script (not run if imported as module):
if __name__ == "__main__":
    ## Application logic starts here; processing steps abstracting complexity into functions
    logger.info("Starting fhir pseudonymization...")

    if not is_stdin_piped():
        logger.error("This script demands piped input data from an xml fhir bundle, eg cat fhir.xml | this-script.py")
        sys.exit(1)

    target = _print_xml_target()
    next(target)  # Prime the generator

    mapping_headings = ["given-names","surname","birthdate","pseudonym"]
    with open(settings.user_mapping_filename, 'w', newline='\n') as f:
        mapping_writer = csv.DictWriter(f, delimiter=settings.user_mapping_separator, quotechar='"', quoting=csv.QUOTE_MINIMAL, fieldnames=mapping_headings, lineterminator='\n')
        mapping_writer.writeheader()

        ## Set up the sax parser
        sp = xml.sax.make_parser()
        sp.setContentHandler(FhirStream(target = target, mapping_output = mapping_writer))
        sp.setFeature(xml.sax.handler.feature_namespaces, 0)

        ## sax parses by emitting events when a tag or data is found, so the response to the events is all handled in the ContentHandler class above
        ## (In particulare, we use the target to control how we use the output)
        sp.parse(sys.stdin)

    logger.info("Script run completed!")
