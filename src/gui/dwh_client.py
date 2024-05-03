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
from PySide6.QtCore import QFile
from PySide6.QtUiTools import loadUiType, QUiLoader
# from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, QTableWidgetItem
import PySide6.QtGui
import re
import subprocess
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
    compatible_java: str = "java"
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(AppMeta().app_name)
logger.setLevel(settings.log_level)
logger.warning("Logging loaded with default configuration")

## Custom modules - use pyinstaller "pathex" when building
## Use "binary" root if available, else python __file__
# guiRoot = os.path.abspath(getattr(sys, '_MEIPASS', os.path.dirname(__file__)))
projectRoot = os.path.abspath(getattr(sys, '_MEIPASS', os.path.join(os.path.dirname(__file__), '..', '..')))
scriptDir = os.path.join(projectRoot, 'src' )
sys.path.append(scriptDir)
import api_processing

## Load the UI exported from qt-designer .ui file
## With: pyside6-uic src/gui/mainWindow.ui -o src/gui/ui_mainwindow.py
from ui_mainwindow import Ui_MainWindow
class DwhClientWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        ## Set the app constants
        self.setWindowTitle(f'{AppMeta().app_name} - {AppMeta().app_version}')
        self.versionIndicatorLabel.setText(f'Version: {AppMeta().app_version}')
        self.versionIndicatorLabel.setToolTip(AppMeta().app_description)
        self.setWindowIcon(PySide6.QtGui.QIcon(os.path.join(projectRoot, 'resources', 'DzlLogoSymmetric.webp')))
        ## Button actions (LOCAL) - can't I define these in the QT Designer GUI via slots and signals?
        self.dsConfigFileInputPushButton.clicked.connect(self.dsConfigFilePicker_clicked)
        self.rawFhirFileInputPushButton.clicked.connect(self.rawFhirFilePicker_clicked)
        self.dwhFhirFileOutputPushButton.clicked.connect(self.dwhFhirFilePicker_clicked)
        if settings.secret_key != "ChangeMe":
            self.secretKeyPasswordEdit.setText(settings.secret_key)
        # self.pseudonymizeButton.hover.connect(self.pseudonymizeButton_hover)
        self.generateFhirButton.installEventFilter(self)
        self.pseudonymizeButton.installEventFilter(self)
        ## Button actions (DWH) - can't I define these in the QT Designer GUI via slots and signals?
        self.apiConnectPushButton.clicked.connect(self.getDsList)
        self.dsFileInputPushButton.clicked.connect(self.dwhUploadFhirFilePicker_clicked)
        # self.newDsUploadPushButton.clicked.connect(self.uploadSource)
        self.newDsUploadPushButton.installEventFilter(self)
        self.apiUrlEdit.setText(settings.DWH_API_ENDPOINT)
        if settings.dwh_api_key != "ChangeMe":
            self.apiKeyPasswordEdit.setText(settings.dwh_api_key)
        self.dsChooseComboBox.currentTextChanged.connect(self.dsSelected)
        self.deleteSourcePushButton.clicked.connect(self.deleteDs)
        self.updateSourcePushButton.clicked.connect(self.processDs)
        self.showSourceInfoPushButton.clicked.connect(self.showDsInfo)
        self.showSourceErrorPushButton.clicked.connect(self.showDsError)
        self.reloadStatusPushButton.clicked.connect(self.showCurrentSourceStatus)

    def eventFilter(self, obj, ev):
        if ev.type() == PySide6.QtCore.QEvent.Enter:
            # logger.info("Entered obj: %s (from: %s)", obj, str([self.generateFhirButton, self.pseudonymizeButton, self.newDsUploadPushButton]))
            logger.info("Entered obj: %s", obj)
            if obj == self.generateFhirButton:
                self.generateFhirButton_hover()
            elif obj == self.pseudonymizeButton:
                self.pseudonymizeButton_hover()
            elif obj == self.newDsUploadPushButton:
                self.uploadButton_hover()
        return False

    ## LOCAL processing
    def dsConfigFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.dsConfigFileInputText.setText(fileName)
    def rawFhirFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.rawFhirfileInputText.setText(fileName)
        assumedOutFn = os.path.basename(fileName).replace('-raw', '-dwh')
        assumedOutPath = os.path.join(os.path.dirname(fileName), assumedOutFn)
        self.newDsFileEdit.setText(assumedOutPath)
        if self.dwhFhirfileOutputText.text() == "":
            logger.debug("Adding assumed output file path...")
            if assumedOutFn != os.path.basename(fileName):
                self.dwhFhirfileOutputText.setText(assumedOutPath)
    def dwhFhirFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.dwhFhirfileOutputText.setText(fileName)
    def generateFhirButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling generate fhir possibility")
        if self.verifyGeneratePreparedness():
            try: self.generateFhirButton.clicked.disconnect()
            except Exception: pass
            self.generateFhirButton.clicked.connect(self.generateFhir)
            self.generateFhirButton.setStyleSheet("font: bold; color: green")
        else:
            try: self.generateFhirButton.clicked.disconnect()
            except Exception: pass
            self.generateFhirButton.setStyleSheet("font: italic; color: gray")
    def verifyGeneratePreparedness(self) -> bool:
        """ Check we have in/out files """
        logger.info("Checking... %s, %s", self.dsConfigFileInputText.text(), self.rawFhirfileInputText.text())
        if not os.path.exists(self.dsConfigFileInputText.text()):
            logger.warning("Config input test failed")
            return False
        if not os.path.isdir(os.path.dirname(self.rawFhirfileInputText.text())):
            logger.warning("Fhir output test failed")
            return False
        return True
    def generateFhir(self):
        """ Call the exisiting "script" style java code """
        logger.info("Generating fhir started...")
        ## Don't let user click it again while its running
        try: self.generateFhirButton.clicked.disconnect()
        except Exception: pass
        ## NOTE: Can't update while running this (both synchronus methonds on the main window object)
        # self.pseudonymizeButton.setStyleSheet("background-color: yellow; font: italic; color: black;")
        # self.pseudonymizeButton.setText("Processing...")
        # time.sleep(2)
        # logger.info("Nearly there...")
        # self.pseudonymizeButton.setStyleSheet("background-color: green; font: italic; color: black;")
        # time.sleep(1)
        # self.pseudonymizeButton.setStyleSheet("font: italic; color: gray;")
        # self.pseudonymizeButton.setText("Generate Fhir bundle")
        # libsDir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'lib'))
        # libsDir = os.path.abspath(os.path.join(projectRoot, 'resources', 'lib'))
        libsDir = os.path.abspath(os.path.join(projectRoot, 'resources', 'lib'))
        libs = [os.path.join(libsDir, file) for file in next(os.walk(libsDir), (None, None, []))[2] if file.endswith(".jar")] # [] if no file
        javaCp = ':'.join(libs)
        ## Actual work - write streamed output to file
        with open(self.rawFhirfileInputText.text(), 'w') as rawFhir:
            logger.info("Running java subprocess.Popen to generate fhir")
            proc = subprocess.Popen([settings.compatible_java,'-Dfile.encoding=UTF-8', '-cp', javaCp, 'de.sekmi.histream.etl.ExportFHIR', self.dsConfigFileInputText.text()], stdout=subprocess.PIPE)
            # proc = subprocess.Popen(['/usr/lib/jvm/java-8-openjdk/jre/bin/java','-Dfile.encoding=UTF-8', '-cp', javaCp, 'de.sekmi.histream.etl.ExportFHIR', self.dsConfigFileInputText.text()], stdout=subprocess.PIPE)
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                rawFhir.write(line.decode())
        logger.info("Fhir generation complete")

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
        if not os.path.isdir(os.path.dirname(self.dwhFhirfileOutputText.text())):
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
        ## Stream raw fhir as input and write output as stream from streamed stdout
        with open(self.rawFhirfileInputText.text(), 'r') as rawFhir:
            with open(self.dwhFhirfileOutputText.text(), 'w') as dwhFhir:
                psyeudonymEnv = os.environ.copy()
                psyeudonymEnv['secret_key'] = self.secretKeyPasswordEdit.text()
                pseudonymizationScript = os.path.join(projectRoot, 'src', 'stream-pseudonymization.py')
                # proc = subprocess.run([pseudonymizationScript], input=rawFhir.read(), capture_output=True, text=True)
                proc = subprocess.Popen(['python', pseudonymizationScript], stdin=rawFhir, stdout=subprocess.PIPE, env=psyeudonymEnv)
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    dwhFhir.write(line.decode())
        logger.info("Pseudonymisation complete")

    ## DWH processing
    def dwhUploadFhirFilePicker_clicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.newDsFileEdit.setText(fileName)
    def uploadSource(self):
        """ Upload bundle """
        self.sourceInfoErrorBrowser.setText(api_processing.uploadSource(self.newDsNameEdit.text(), self.newDsFileEdit.text()))

    def uploadButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling upload possibility")
        if self.verifyUploadPreparedness():
            try: self.newDsUploadPushButton.clicked.disconnect()
            except Exception: pass
            self.newDsUploadPushButton.clicked.connect(self.uploadSource)
            self.newDsUploadPushButton.setStyleSheet("font: bold; color: green")
        else:
            try: self.newDsUploadPushButton.clicked.disconnect()
            except Exception: pass
            self.newDsUploadPushButton.setStyleSheet("font: italic; color: gray")
    def verifyUploadPreparedness(self) -> bool:
        """ Check we have a real files and source_id no illegal chars """
        logger.info("Checking... %s, %s", self.newDsFileEdit.text(), self.newDsNameEdit.text())
        if not os.path.exists(self.newDsFileEdit.text()):
            logger.debug("No valid file to upload")
            return False
        reFindUnwanted = re.compile(r"[<>{}[\]/\\~`#?!:;*\"']");
        if self.newDsNameEdit.text() is None or len(self.newDsNameEdit.text()) < 3 or  reFindUnwanted.search(self.newDsNameEdit.text()):
            logger.debug("Invalid datasource name (source_id)")
            return False
        return True

    def getDsList(self):
        """ Connect to API and populate list of remote DS's - or show user an error
        Also update the "connect" button to "connected/refresh list"
        """
        ## Connect - well, update settings to allow connection
        api_processing.settings.DWH_API_ENDPOINT = self.apiUrlEdit.text()
        api_processing.settings.dwh_api_key = self.apiKeyPasswordEdit.text()
        ## Update sources list
        sources = api_processing.listDwhSources()
        if sources is not None:
            logger.debug("Found sources: %s", sources)
            self.dsChooseComboBox.clear()
            self.dsChooseComboBox.addItems(sources)
            self.apiConnectPushButton.setText("Connected/refresh list")
            self.apiConnectPushButton.setStyleSheet("background-color: green; font: bold; color: black;")
        else:
            logger.warning("Could not connect to api (%s)", api_processing.settings.DWH_API_ENDPOINT)

    def dsSelected(self, source_id: str):
        """ Update selected DS """
        self.selectedSourceId = source_id
        self.showCurrentSourceStatus()
    def showCurrentSourceStatus(self):
        """ Show user status of selected source """
        dsStatus = api_processing.sourceStatus(self.selectedSourceId)
        self.dsStatusTableWidget.setItem(0, 0, QTableWidgetItem(dict.get(dsStatus, 'source_id', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 1, QTableWidgetItem(dict.get(dsStatus, 'status', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 2, QTableWidgetItem(dict.get(dsStatus, 'sourcesystem_cd', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 3, QTableWidgetItem(dict.get(dsStatus, 'last_activity', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 4, QTableWidgetItem(dict.get(dsStatus, 'last_update', 'Unavailable')))
    def deleteDs(self):
        """ Simply call delete endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.deleteSource(self.selectedSourceId))
    def processDs(self):
        """ Simply call process endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.processSource(self.selectedSourceId))
    def showDsInfo(self):
        """ Simply call info endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.getSourceInfo(self.selectedSourceId))
    def showDsError(self):
        """ Simply call error endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.getSourceError(self.selectedSourceId))


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
