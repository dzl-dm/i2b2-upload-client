#!/usr/bin/env python3
"""
Description: Pseudonymise an XML fhir bundle by hashing the PID and removing other name related tags
Input: Fhir bundle xml line by line via stdin
Output: fhir bundle xml via std out
stderr: for logs

Usage: cat ./tmp/sample-fhir.xml | src/stream-pseudonymization.py > tmp/sample-fhir-pseudonyms.xml 2>> log/pseudonymisation.log
Explainer: Each entry is loaded into memory in turn, if its a patient, its pseudonymised, then its written
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
    secret_key: str

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
    def __init__(self):
        """ Ensure the XML definition is written
        Also setup the monitoring dict to detect clashes
        """
        self.currentEntryResourceType:str = None
        self.currentSubElement = lxml.sax.ElementTreeContentHandler()
        self.currentDepth:int = 0
        self.currentPatient:int = None
        self.currentEncounter:int = None

        ## Write the xml declaration (to stdout)
        print('<?xml version="1.0" ?>')

    def startElement(self, name, attrs):
        """ Depending on the element, build up the Entry sub-element in lxml """
        self.currentDepth += 1
        if name == "Bundle":
            ## Reconstruct the Bundle opening tag
            attrText = ', '.join([f'{k}="{v}"' for k,v in attrs.items()])
            print(f'<Bundle {attrText}>')
            pass
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
            #logger.debug('sending startElement "%s" with attrs "%s" to lxml', name, attrPairsNS)
            self.currentSubElement.startElementNS((None, name), name, attrPairsNS)
            #logger.debug('self.currentEntryResourceType: %s', self.currentEntryResourceType)
            #logger.debug('self.currentDepth: %s', self.currentDepth)
            #logger.debug('self.currentPatient: %s', self.currentPatient)
            #logger.debug('self.currentEncounter: %s', self.currentEncounter)
            #logger.debug('<%s %s>',name, attrPairsNS)

    def characters(self, cdata):
        """ Future proof in case we have cData in our bundle in the future """
        txt_str = cdata.strip()
        if len(txt_str) > 0:
            #logger.debug('sending cData to lxml')
            self.currentSubElement.characters(cdata)
        #logger.debug('self.currentEntryResourceType: %s', self.currentEntryResourceType)
        #logger.debug('self.currentPatient: %s', self.currentPatient)
        #logger.debug('self.currentEncounter: %s', self.currentEncounter)
        #logger.debug('cData: %s', cdata)

    def endElement(self, name):
        """ If ending an entry, its time to evaluate if we pseudonymize before writing to stdout """
        self.currentDepth -= 1
        if name == "Bundle":
            ## Write the Bundle closing tag (to stdout)
            print('</Bundle>')
        else:
            #logger.debug('sending endElement to lxml')
            self.currentSubElement.endElementNS((None, name), name)
            ## Debug output...
            #logger.debug('self.currentEntryResourceType: %s', self.currentEntryResourceType)
            #logger.debug('self.currentPatient: %s', self.currentPatient)
            #logger.debug('self.currentEncounter: %s', self.currentEncounter)
            #logger.debug('</%s>', name)
            #logger.debug('self.currentDepth: %s', self.currentDepth)
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
        # treeXml = lxml.etree.tostring(self.currentSubElement.etree.getroot(), pretty_print=True).decode('UTF-8')
        treeXml = lxml.etree.tostring(self.currentSubElement.etree.getroot(), pretty_print=False).decode('UTF-8')
        print(treeXml)
        # self.fh.write(treeXml)
        # tree.write(sys.stdout, pretty_print=True)
        # treeXml.write(sys.stdout, pretty_print=True)

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
        if len(self.currentSubElement.etree.xpath("//resource/Patient/name")) > 1:
            logger.warning("Patient '%s' has more than 1 'name' entry, removing all, 1st occurance used for pseudonymization", self.currentPatient)
        for nameElem in self.currentSubElement.etree.xpath("//resource/Patient/name"):
            self.currentSubElement.etree.xpath("//resource/Patient")[0].remove(nameElem)

    def _validAttrib(self, xpathAttrib) -> str:
        if len(xpathAttrib) == 1:
            return xpathAttrib[0]
        elif len(xpathAttrib) > 1:
            logger.warning("There are multiple matching attributes (returning 1st)! '%s'", xpathAttrib)
            return xpathAttrib[0]
        else:
            return ""

def _hash_ids(given_name:str, surname:str, birthdate:str, salt:str = settings.secret_key, sep:str = "|") -> str:
    """ Hash the combination of:
        * salt
        * given-name
        * surname
        * birthdate
        with the local secret-key as the salt
    """
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

## When called as script (not run if imported as module):
if __name__ == "__main__":
    ## Application logic starts here; processing steps abstracting complexity into functions
    logger.info("Starting fhir pseudonymization...")

    if not is_stdin_piped():
        logger.error("This script demands piped input data from an xml fhir bundle, eg cat fhir.xml | this-script.py")
        sys.exit(1)

    ## Set up the sax parser
    sp = xml.sax.make_parser()
    sp.setContentHandler(FhirStream())
    sp.setFeature(xml.sax.handler.feature_namespaces, 0)

    ## sax parses by emitting events when a tag or data is found, so the response to the events is all handled in the ContentHandler class above
    sp.parse(sys.stdin)

    logger.info("Script run completed!")
