#!/usr/bin/env python3
"""
Description: A PySide6 (QT6) interactive GUI to upload fhir bundle to DWH server API
stderr: for logs

Usage: dwh-client.exe 2>> log/dwh-client.log
Explainer: See which sources you have, trigger processing, delete them, update them or add new ones
"""

## Import built-ins
import gzip
import os
import re
import subprocess
import sys
import time

## Import third party libraries
import datetime
import importlib.metadata
import logging
from pydantic_settings import BaseSettings
## Bad practice, loading .ui file in code: https://doc.qt.io/qtforpython-6.2/PySide6/QtUiTools/loadUiType.html
# from PySide6 import uic
from PySide6.QtCore import QFile
from PySide6.QtUiTools import loadUiType, QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, QTableWidgetItem, QMessageBox
import PySide6.QtGui

class AppMeta():
    """ Purely constants """
    app_name: str = "i2b2-upload-client"
    app_sub_name: str = "DWH Upload Client"
    app_description: str = "A PySide6 (QT6) interactive GUI to upload fhir bundle to DWH server API"
    app_version: None|str = None

## ---------------- ##
## Create  settings ##
## ---------------- ##
class Settings(BaseSettings):
    """ The variables defined here will be taken from env vars if available and matching the type hint """
    log_level: str = "WARNING"
    log_format: str = "[%(asctime)s] {%(name)s/%(module)s:%(lineno)d (%(funcName)s)} %(levelname)s - %(message)s"
    secret_key: str = "ChangeMe"
    # DWH_API_ENDPOINT: str = "http://localhost/api"
    DWH_API_ENDPOINT: str = "https://data.dzl.de/api"
    dwh_api_key: str = "ChangeMe"
    compatible_java: str = "java"
settings = Settings()

## Load logger for this file/script
formatter = logging.Formatter(settings.log_format)
logging.basicConfig(format=settings.log_format)
## Set app's logger level and format...
logger = logging.getLogger(AppMeta().app_sub_name)
logger.setLevel(settings.log_level)
logger.warning("Logging loaded with default configuration")


## Custom modules - use pyinstaller "pathex" when building
## Use "binary" root if available, else python __file__
projectRoot = os.path.abspath(getattr(sys, '_MEIPASS', os.path.join(os.path.dirname(__file__), '..', '..')))
scriptDir = os.path.join(projectRoot, 'src' )
sys.path.append(scriptDir)
import api_processing

def get_version():
    """ Get version dynamically from pyprojects.toml if possible and update static file. 
    Else, read from static file. Else 'unknown' """
    version = "Unknown"
    version_file = os.path.join(projectRoot, "build", "version.txt")
    version_file_built = os.path.join(projectRoot, "version.txt")
    logger.debug("Checking version...")

    try:
        version = importlib.metadata.version(AppMeta.app_name)
        logger.warning("Found version '%s', setting to file '%s'", version, version_file)
        with open(version_file, "w") as version_file:
            version_file.write(version)
    except importlib.metadata.PackageNotFoundError:
        logger.error("Found error 'importlib.metadata.PackageNotFoundError' (metadata not available, attempting to read version file)")
        if os.path.exists(version_file) and os.path.isfile(version_file):
            with open(version_file, "r") as version_file:
                version = version_file.read()
        elif os.path.exists(version_file_built) and os.path.isfile(version_file_built):
            with open(version_file_built, "r") as version_file:
                version = version_file.read()
        else:
            logger.error("Version file '%s' not available, setting version to 'Unknown'", version_file_built)
            version = "Unknown"
    logger.info("Setting version: %s", version)
    return version

## Populate app_version from pyproject.toml
if not AppMeta.app_version:
    AppMeta.app_version = get_version()


## Load the UI exported from qt-designer .ui file
## With: pyside6-uic src/gui/mainWindow.ui -o src/gui/ui_mainwindow.py
from ui_mainwindow import Ui_MainWindow
class DwhClientWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        ## Set the app constants
        self.setWindowTitle(AppMeta().app_sub_name)
        self.versionIndicatorLabel.setText(f'Version: {AppMeta().app_version}')
        self.versionIndicatorLabel.setToolTip(AppMeta().app_description)
        self.setWindowIcon(PySide6.QtGui.QIcon(os.path.join(projectRoot, 'resources', 'DzlLogoSymmetric.webp')))
        ## Button actions (LOCAL) - can't I define these in the QT Designer GUI via slots and signals?
        self.dsConfigFileInputPushButton.clicked.connect(self.dsConfigFilePickerClicked)
        self.dsConfigFileText.textChanged.connect(self.dsConfigFileChanged)
        self.rawFhirFileInputPushButton.clicked.connect(self.rawFhirFilePickerClicked)
        self.rawFhirFileText.textChanged.connect(self.rawFhirFileChanged)
        self.generateFhirButton.clicked.connect(self.generateFhir)
        self.dwhFhirFileOutputPushButton.clicked.connect(self.dwhFhirFilePickerClicked)
        self.dwhFhirFileText.textChanged.connect(self.dwhFhirFileChanged)
        self.secretKeyPasswordEdit.textChanged.connect(self.secretKeyPasswordChanged)
        self.pseudonymizeButton.clicked.connect(self.pseudonymizeFhir)

        if settings.secret_key != "ChangeMe":
            self.secretKeyPasswordEdit.setText(settings.secret_key)
        # self.pseudonymizeButton.hover.connect(self.pseudonymizeButton_hover)
        self.generateFhirButton.installEventFilter(self)
        self.pseudonymizeButton.installEventFilter(self)
        ## Button actions (DWH) - can't I define these in the QT Designer GUI via slots and signals?
        self.apiConnectPushButton.clicked.connect(self.getDsList)
        self.dsFileInputPushButton.clicked.connect(self.dwhUploadFhirFilePickerClicked)
        # self.newDsUploadPushButton.clicked.connect(self.uploadSource)
        self.newDsUploadPushButton.installEventFilter(self)
        self.apiUrlEdit.setText(settings.DWH_API_ENDPOINT)
        if settings.dwh_api_key != "ChangeMe":
            self.apiKeyPasswordEdit.setText(settings.dwh_api_key)
        self.dsChooseComboBox.currentTextChanged.connect(self.dsSelected)
        self.newDsUploadPushButton.clicked.connect(self.uploadSource)
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
    def dsConfigFilePickerClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"Choose datasource configuration file", "","All Files (*)", options=options)
        if fileName:
            self.dsConfigFileText.setText(fileName)
    def dsConfigFileChanged(self):
        """ Try to auto-fill the raw fhir based on path of datasource.xml """
        if self.rawFhirFileText.text() == "":
            logger.debug("Adding assumed raw fhir file path...")
            assumedRawFhirFn = os.path.join(os.path.dirname(self.dsConfigFileText.text()), 'client-output', 'fhir-bundle-raw.xml')
            self.rawFhirFileText.setText(assumedRawFhirFn)
    def rawFhirFilePickerClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"Choose raw fhir xml file", "","All Files (*)", options=options)
        if fileName:
            self.rawFhirFileText.setText(fileName)
    def rawFhirFileChanged(self):
        """ Try to enable generate fhir button and auto-fill dwh fhir """
        if self.dwhFhirFileText.text() == "":
            logger.debug("Adding assumed dwh fhir file path...")
            assumedDwhFhirFn = os.path.join(os.path.dirname(self.rawFhirFileText.text()), os.path.basename(self.rawFhirFileText.text()).replace('-raw', '-dwh'))
            self.dwhFhirFileText.setText(assumedDwhFhirFn)
        self.generateFhirButton_hover()
    def dwhFhirFilePickerClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"Choose dwh fhir xml file", "","All Files (*)", options=options)
        if fileName:
            self.dwhFhirFileText.setText(fileName)
    def dwhFhirFileChanged(self):
        """ Try to enable pseudonymize button and update the DWH tab's upload file """
        self.pseudonymizeButton_hover()
        self.newDsFileEdit.setText(self.dwhFhirFileText.text())
    def secretKeyPasswordChanged(self):
        """ Try to enable pseudonymize button """
        self.pseudonymizeButton_hover()
    def generateFhirButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling generate fhir possibility")
        if self.verifyGeneratePreparedness():
            self.generateFhirButton.setEnabled(True)
            self.generateFhirButton.setStyleSheet("font: bold; color: green")
        else:
            self.generateFhirButton.setEnabled(False)
            self.generateFhirButton.setStyleSheet("font: italic; color: gray")
    def verifyGeneratePreparedness(self) -> bool:
        """ Check we have in/out files """
        logger.info("Checking... %s, %s", self.dsConfigFileText.text(), self.rawFhirFileText.text())
        if not os.path.exists(self.dsConfigFileText.text()):
            logger.warning("Config input test failed (%s)", self.dsConfigFileText.text())
            return False
        if not os.path.isdir(os.path.dirname(self.rawFhirFileText.text())):
            if os.path.isdir(os.path.dirname(os.path.dirname(self.rawFhirFileText.text()))):
                ## If parent of output dir exists, simply add the last directory level (eg <project>/client-output/)
                os.mkdir(os.path.dirname(self.rawFhirFileText.text()))
                return True
            logger.warning("Fhir output test failed (%s)", os.path.dirname(self.rawFhirFileText.text()))
            return False
        return True
    def generateFhir(self):
        """ Call the exisiting "script" style java code """
        logger.info("Generating fhir started...")
        ## Don't let user click it again while its running
        self.generateFhirButton.setEnabled(False)
        libsDir = os.path.abspath(os.path.join(projectRoot, 'resources', 'lib'))
        libs = [os.path.join(libsDir, file) for file in next(os.walk(libsDir), (None, None, []))[2] if file.endswith(".jar")] # [] if no file
        javaCpSep = ':'
        if os.name == 'nt':
            ## Windows class path separator
            javaCpSep = ';'
        javaCp = javaCpSep.join(libs)
        proc = None
        ## Actual work - write streamed output to file
        with open(self.rawFhirFileText.text(), 'w') as rawFhir:
            logger.info("Running java subprocess.Popen to generate fhir")
            proc = subprocess.Popen([settings.compatible_java,'-Dfile.encoding=UTF-8', '-cp', javaCp, 'de.sekmi.histream.etl.ExportFHIR', self.dsConfigFileText.text()], stdout=subprocess.PIPE)
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                rawFhir.write(line.decode())
        proc.communicate()
        if proc.returncode == 0:
            self.stage1StatusLabel.setText("<b style='color:green; font-size:12pt;'>Status:</b>")
            self.stage1StatusText.setText("Completed successfully!")
            logger.info("Fhir generation complete")
        else:
            self.stage1StatusLabel.setText("<b style='color:red; font-size:12pt;'>Status:</b>")
            self.stage1StatusText.setText(f"Processing failed with return code: '{proc.returncode}'<br/>Please check your datasource.xml mapping configuration. Ensure you have timezone set (see readme for guidance)")
            logger.error("Fhir generation had errors (return code: %s)...", proc.returncode)

    def pseudonymizeButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling pseudonymisation possibility")
        if self.verifyPseudonymisationPreparedness():
            self.pseudonymizeButton.setEnabled(True)
            self.pseudonymizeButton.setStyleSheet("font: bold; color: green")
        else:
            self.pseudonymizeButton.setEnabled(False)
            self.pseudonymizeButton.setStyleSheet("font: italic; color: gray")
    def verifyPseudonymisationPreparedness(self) -> bool:
        """ Check we have in/out files and a secret_key """
        logger.info("Checking... %s, %s, <secret_key>", self.rawFhirFileText.text(), self.dwhFhirFileText.text())
        if not os.path.exists(self.rawFhirFileText.text()):
            logger.warning("Input test failed")
            return False
        if not os.path.isdir(os.path.dirname(self.dwhFhirFileText.text())):
            logger.warning("Output test failed")
            return False
        if self.secretKeyPasswordEdit.text() is None or len(self.secretKeyPasswordEdit.text()) < 4 or self.secretKeyPasswordEdit.text() in ["", "ChangeMe"]:
            logger.warning("secret_key test failed")
            return False
        return True
    def pseudonymizeFhir(self):
        """ Call the exisiting "script" style python code """
        logger.info("Pseudonymisation started...")
        # try: self.pseudonymizeButton.clicked.disconnect()
        # except Exception: pass
        self.pseudonymizeButton.setEnabled(False)
        proc = None
        ## Stream raw fhir as input and write output as stream from streamed stdout
        with open(self.rawFhirFileText.text(), 'r') as rawFhir:
            with open(self.dwhFhirFileText.text(), 'w') as dwhFhir:
                psyeudonymEnv = os.environ.copy()
                psyeudonymEnv['secret_key'] = self.secretKeyPasswordEdit.text()
                pseudonymizationScript = os.path.join(projectRoot, 'src', 'stream_pseudonymization.py')
                # proc = subprocess.run([pseudonymizationScript], input=rawFhir.read(), capture_output=True, text=True)
                proc = subprocess.Popen(['python', pseudonymizationScript], stdin=rawFhir, stdout=subprocess.PIPE, env=psyeudonymEnv)
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    dwhFhir.write(line.decode())
        proc.communicate()
        if proc.returncode == 0:
            # self.stage2StatusLabel.append(f"<b>Stage 2:</b> Completed successfully!")
            self.stage2StatusLabel.setText("<b style='color:green; font-size:12pt;'>Status:</b>")
            self.stage2StatusText.setText('<html><head/><body><p><span style=" font-size:12pt; font-weight:600;">Stage 2:</span> Completed successfully!</p></body></html>')
            logger.info("Pseudonymization complete")
        else:
            # self.stage2StatusLabel.append(f"<b>Stage 2:</b> Pseudonymization failed with return code: '{proc.returncode}'<br/>Please check all file references are correct and that stage 1 has completed successfully.")
            self.stage2StatusLabel.setText("<b style='color:red; font-size:12pt;'>Status:</b>")
            self.stage2StatusText.setText(f'<html><head/><body><p><span style=" font-size:12pt; font-weight:600;">Stage 2:</span> Pseudonymization failed with return code: \'{proc.returncode}\'<br/>Please check all file references are correct and that stage 1 has completed successfully.</p></body></html>')
            logger.error("Pseudonymization had errors (return code: %s)...", proc.returncode)

    ## DWH processing
    def dwhUploadFhirFilePickerClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"Choose dwh-ready fhir xml file", "","All Files (*)", options=options)
        if fileName:
            self.newDsFileEdit.setText(fileName)
    def uploadSource(self):
        """ User confirm, then upload bundle """
        source_id = self.newDsNameEdit.text()
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle("Confirm action")
        confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation.setText(f"Are you sure you want to upload new data for <b>'{source_id}'</b> from file:<br/><br/>{self.newDsFileEdit.text()}")
        response = confirmation.exec()

        if response == QMessageBox.Yes:
            logger.info("Uploading new data for '%s'", source_id)
            self.informUserApi(f"[{nowTimeStamp()}] Starting upload", clearInfo=True)
            ## If file big enough (over 1mb), compress before upload
            realUploadFilePath = self.newDsFileEdit.text()
            if os.path.getsize(self.newDsFileEdit.text()) > 1000000:
                logger.info("Compressing before upload...")
                self.informUserApi(f"[{nowTimeStamp()}] Compressing before upload...")
                ## TODO: The uplaod is currently hard-coded to always be saved with this name, even if compressed
                serverBundleName = "fhir-bundle.xml"
                realUploadFilePath = os.path.join(os.path.dirname(self.newDsFileEdit.text()), "upload.gz")
                if os.path.basename(self.newDsFileEdit.text()) != serverBundleName:
                    os.rename(self.newDsFileEdit.text(), os.path.join(os.path.dirname(self.newDsFileEdit.text()), serverBundleName))
                with open(os.path.join(os.path.dirname(self.newDsFileEdit.text()), serverBundleName), 'rb') as f_in:
                    with gzip.open(realUploadFilePath, 'wb') as f_out:
                        ## Write the gzipped file
                        f_out.writelines(f_in)
                if os.path.basename(self.newDsFileEdit.text()) != serverBundleName:
                    os.rename(os.path.join(os.path.dirname(self.newDsFileEdit.text()), serverBundleName), self.newDsFileEdit.text())
            self.informUserApi(f"[{nowTimeStamp()}] Uploading...")
            self.sourceInfoErrorBrowser.append(f"<b>API response:</b> {api_processing.uploadSource(source_id, realUploadFilePath)}")
            if realUploadFilePath != self.newDsFileEdit.text():
                os.remove(realUploadFilePath)
            self.informUserApi(f"[{nowTimeStamp()}] Upload complete, check status.")
            self.uploadCompletion(source_id)
    def uploadCompletion(self, source_id: str):
        """ Post upload processing """
        logger.info("Processing upload completion for source: %s", source_id)
        self.getDsList()
        # if self.getUserId() is not None:
            # source_id = f"{self.getUserId()}_{source_id}"
            # self.dsSelected(source_id)
        index = self.dsChooseComboBox.findText(source_id)
        logger.debug("Updating combo box with source (%s): %s", index, source_id)
        if index >= 0:
            self.dsChooseComboBox.setCurrentIndex(index)
            self.dsSelected(source_id)
    def getUserId(self):
        """ First use prefix of first item """
        userId = None
        if self.dsChooseComboBox.count() > 0:
            userId = self.dsChooseComboBox.itemText(0).split("_")[0]
        log.debug("UserId: %s", userId)
        return userId

    def uploadButton_hover(self):
        """ Verify and enable/disable click action """
        logger.info("Verifying and enabling/disabling upload possibility")
        if self.verifyUploadPreparedness():
            self.newDsUploadPushButton.setEnabled(True)
            self.newDsUploadPushButton.setStyleSheet("font: bold; color: green")
        else:
            self.newDsUploadPushButton.setEnabled(False)
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
        self.informUserApi(f"[{nowTimeStamp()}] Connecting to server and updating source list...", clearInfo=True)
        ## Update sources list
        sources = api_processing.listDwhSources()
        if sources is not None:
            logger.debug("Found sources: %s", sources)
            self.dsChooseComboBox.clear()
            self.dsChooseComboBox.addItems(sources)
            self.apiConnectPushButton.setText("Connected/refresh list")
            self.apiConnectPushButton.setStyleSheet("background-color: green; font: bold; color: black;")
            self.reloadStatusPushButton.setStyleSheet("background-color: green; font: bold; color: black;")
            self.informUserApi(f"[{nowTimeStamp()}] Connected, please select a source to work with from the dropdown or upload a new source")
        else:
            logger.warning("Could not connect to api (%s)", api_processing.settings.DWH_API_ENDPOINT)
            self.informUserApi(f"[{nowTimeStamp()}] Could not connect to api ({api_processing.settings.DWH_API_ENDPOINT})")

    def dsSelected(self, source_id: str):
        """ Update selected DS """
        logger.info("Selecting source and showing info for: %s", source_id)
        self.sourceInfoErrorBrowser.clear()
        if not source_id:
            self.selectedSourceId = None
        else:
            self.selectedSourceId = source_id
            selectedSourceStatus = self.showCurrentSourceStatus()
            # logger.debug("Selected source status: %s", selectedSourceStatus)
            self.newDsNameEdit.setText(self.selectedSourceId)
            logger.debug("status: %s", dict.get(selectedSourceStatus, 'status', 'Unavailable'))
            # if dict.get(selectedSourceStatus, 'status', 'Unavailable') == 'Uploaded':
            if 'status' in selectedSourceStatus and selectedSourceStatus['status'] == 'Uploaded':
                logger.debug("Setting link line to green")
                self.uploadProcessLinkLine.setStyleSheet("color: green")
                self.uploadProcessLinkLine_2.setStyleSheet("color: green")
                self.uploadProcessLinkLine_3.setStyleSheet("color: green")
                self.updateSourcePushButton.setStyleSheet("background-color: green; font: bold; color: black;")
            else:
                logger.debug("Setting link line to grey")
                self.uploadProcessLinkLine.setStyleSheet("color: gray")
                self.uploadProcessLinkLine_2.setStyleSheet("color: gray")
                self.uploadProcessLinkLine_3.setStyleSheet("color: gray")
                self.updateSourcePushButton.setStyleSheet("")
    def showCurrentSourceStatus(self) -> dict:
        """ Show user status of selected source """
        dsStatus = api_processing.sourceStatus(self.selectedSourceId)
        self.dsStatusTableWidget.setItem(0, 0, QTableWidgetItem(dict.get(dsStatus, 'source_id', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 1, QTableWidgetItem(dict.get(dsStatus, 'status', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 2, QTableWidgetItem(dict.get(dsStatus, 'sourcesystem_cd', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 3, QTableWidgetItem(dict.get(dsStatus, 'last_activity', 'Unavailable')))
        self.dsStatusTableWidget.setItem(0, 4, QTableWidgetItem(dict.get(dsStatus, 'last_update', 'Unavailable')))
        return dsStatus
    def deleteDs(self):
        """ User confirm, then call delete endpoint and show response """
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle("Confirm action")
        confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation.setText(f"Are you sure you want to delete data for <b>'{self.selectedSourceId}'</b>?<br/><br/>This will remove the data from the database and any files on the server with data.")
        response = confirmation.exec()

        if response == QMessageBox.Yes:
            self.informUserApi(f"[{nowTimeStamp()}] Connecting to server and deleting source...", clearInfo=True)
            self.sourceInfoErrorBrowser.setText(api_processing.deleteSource(self.selectedSourceId))
            time.sleep(0.2)
            self.showCurrentSourceStatus()

    def processDs(self):
        """ User confirm, then call process endpoint and show response """
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle("Confirm action")
        confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation.setText(f"Are you sure you want to process data for <b>'{self.selectedSourceId}'</b>?<br/><br/>This will process the fhir-bundle into the DWH database so it can be queried with the query tool.")
        response = confirmation.exec()

        if response == QMessageBox.Yes:
            self.informUserApi(f"[{nowTimeStamp()}] Connecting to server and processing source...", clearInfo=True)
            self.sourceInfoErrorBrowser.setText(api_processing.processSource(self.selectedSourceId))
            self.informUserApi(f"[{nowTimeStamp()}] Processing can take some time, reload the status to view progress...")
            time.sleep(0.2)
            self.showCurrentSourceStatus()
    def showDsInfo(self):
        """ Simply call info endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.getSourceInfo(self.selectedSourceId))
        self.showCurrentSourceStatus()
    def showDsError(self):
        """ Simply call error endpoint and show response """
        self.sourceInfoErrorBrowser.setText(api_processing.getSourceError(self.selectedSourceId))
        self.showCurrentSourceStatus()

    def informUserApi(self, infoText:str, clearInfo:bool = False):
        """ Display some text to user about what the client is doing """
        if clearInfo:
            self.sourceInfoErrorBrowser.setText(infoText)
        else:
            self.sourceInfoErrorBrowser.append(infoText)

def nowTimeStamp() -> str:
    """ Simply return the formatted current datetime 
    TODO: Better would be to leverage the logging module even for user feedback """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # return f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"

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
