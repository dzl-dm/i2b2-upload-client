#!/usr/bin/env python3
"""
Description: A PySide6 (QT6) interactive GUI to upload fhir bundle to DWH server API
stderr: for logs

Usage: dwh-client.exe 2>> log/dwh-client.log
Explainer: See which sources you have, trigger processing, delete them, update them or add new ones
"""

## library imports
import logging
import os
from pydantic_settings import BaseSettings
import PySide6
## Bad practice, loading .ui file in code: https://doc.qt.io/qtforpython-6.2/PySide6/QtUiTools/loadUiType.html
# from PySide6 import uic
from PySide6.QtUiTools import loadUiType
# from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog
import sys
import time



class AppMeta():
    """ Purely constants """
    app_name: str = "DWH client"
    app_description: str = "A PySide6 (QT6) interactive GUI to upload fhir bundle to DWH server API"
    app_version: str = "0.0.1-alpha"

## ---------------- ##
## Create  settings ##
## ---------------- ##
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    secret_key: str = "ChangeMe"
    DWH_API_ENDPOINT: str = "http://localhost/api"
    dwh_api_key: str = "ChangeMe"
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(AppMeta().app_name)
logger.setLevel(settings.log_level)
logger.warning("Logging loaded with default configuration")

## Bad practice, loading .ui file in code: https://doc.qt.io/qtforpython-6.2/PySide6/QtUiTools/loadUiType.html
# form_class = uic.loadUiType("mainWindow.ui")[0]  ## Load the UI
form_class = loadUiType("mainWindow.ui")[0]  ## Load the UI
class DwhClientWindow(QMainWindow, form_class):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        ## Set the app constants
        self.setWindowTitle(f'{AppMeta().app_name} - {AppMeta().app_version}')
        self.versionIndicatorLabel.setText(AppMeta().app_version)
        self.versionIndicatorLabel.setToolTip(AppMeta().app_description)
        ## Button actions - can't I define these in the QT Designer GUI via slots and signals?
        self.rawFhirFileInputPushButton.clicked.connect(self.rawFhirFilePicker_clicked)
        self.dwhFhirFileOutputPushButton.clicked.connect(self.dwhFhirFilePicker_clicked)
        if settings.secret_key != "ChangeMe":
            self.secretKeyPasswordEdit.setText(settings.secret_key)
        # self.pseudonymizeButton.hover.connect(self.pseudonymizeButton_hover)
        self.pseudonymizeButton.installEventFilter(self)

    def rawFhirFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.rawFhirfileInputText.setText(fileName)
    def dwhFhirFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.dwhFhirfileOutputText.setText(fileName)
    def pseudonymizeButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling pseudonymisation possibility")
        if self.verifyPseudonymisationPreparedness():
            try: self.pseudonymizeButton.clicked.disconnect()
            except Exception: pass
            self.pseudonymizeButton.clicked.connect(self.pseudonymizeFhir)
            self.pseudonymizeButton.setStyleSheet("font: bold; color: green")
        else:
            # logger.warning("Disconnecting... %s", self.pseudonymizeButton.clicked.connect())
            try: self.pseudonymizeButton.clicked.disconnect()
            except Exception: pass
            self.pseudonymizeButton.setStyleSheet("font: italic; color: gray")
    def verifyPseudonymisationPreparedness(self) -> bool:
        """ Check we have in/out files and a secret_key """
        logger.info("Checking... %s, %s, %s", self.rawFhirfileInputText.text(), self.dwhFhirfileOutputText.text(), self.secretKeyPasswordEdit.text())
        if not os.path.exists(self.rawFhirfileInputText.text()):
            logger.warning("Input test failed")
            return False
        if not os.path.exists(self.dwhFhirfileOutputText.text()):
            logger.warning("Output test failed")
            return False
        if self.secretKeyPasswordEdit.text() is None or len(self.secretKeyPasswordEdit.text()) < 4 or self.secretKeyPasswordEdit.text() in ["", "ChangeMe"]:
            logger.warning("secret_key test failed")
            return False
        return True
    def pseudonymizeFhir(self):
        """ Call the exisiting "script" style python code """
        logger.info("Pseudonymisation started...")
        try: self.pseudonymizeButton.clicked.disconnect()
        except Exception: pass
        ## NOTE: Can't update while running this (both synchronus methonds on the main window object)
        self.pseudonymizeButton.setStyleSheet("background-color: yellow; font: italic; color: black;")
        self.pseudonymizeButton.setText("Processing...")
        time.sleep(2)
        logger.info("Nearly there...")
        self.pseudonymizeButton.setStyleSheet("background-color: green; font: italic; color: black;")
        time.sleep(1)
        self.pseudonymizeButton.setStyleSheet("font: italic; color: gray;")
        self.pseudonymizeButton.setText("Pseudonymize")
        ## Actual work
        
        logger.info("Pseudonymisation complete")

    def eventFilter(self, obj, ev):
        if ev.type() == PySide6.QtCore.QEvent.Enter:
            logger.info("Entered obj: %s", obj)
            if obj == self.pseudonymizeButton:
                self.pseudonymizeButton_hover()
        return False


if __name__ == '__main__':
    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)
    # loader = QUiLoader()

    ## Create a Qt widget, which will be our window.
    # window = QMainWindow()
    window = DwhClientWindow()
    # window = loader.load("mainWindow.ui", None)
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    ## Start the event loop.
    app.exec()

    ## Your application won't reach here until you exit and the event
    ## loop has stopped.
    logger.info("GUI client closed!")
