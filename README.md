# i2b2 upload client
This application uses 3 components to upload patient data to a Data Warehouse. To use the application, you do not need to have a technical understanding of each part, they are however visible as a user so you must be aware of the broad process and what is required of you at each stage. Each stage can be run independently from the other.
1. Convert CSV data into standardized a FHIR bundle in XML format
1. Pseudonymize the identifiable data (if it isn't already)
1. Upload to the DWH and manage the status of the data

## Stage 1: FHIR conversion
We use a helper file, usually call this the `datasource.xml`. Its a custom xml definition of how the csv patient data is formatted after your custom transformation (which files, which columns map to which parameters, etc). A java program uses the XML configuration to convert the data.

## Stage 2: Pseudonymization
Data protection is very important, so this stage removes the name information and creates a non-reversible (but still deterministic) ID as the pseudonym for the patient. You must provide a secret key (a long, random string you generate yourself and keep secret) so that only you generate the pseudonym for the patients. If someone else were to run this stage with their secret key, it would not produce compatible pseudonyms. Record linkage can be achieved by sharing the secret key. This makes sense in environments where multiple people manage different parts of the same data set.

## Stage 3: Upload and DWH management
You can add, update and delete the data in this stage. You must provide your API key (will be provided to you when you are invited to use the upload system). You can also view the status of each source that you have already added to the DWH. Important to note, is that the upload and processing parts of "adding" a data source are separate. You must manually tell the DWH to process the uploaded data once the upload is complete.

# The GUI client
I have developed a Graphical User Interface (GUI) which uses the same background code as the [command line client](#the-cli-client). It "simply" adds an visual interface to make the process more intuitive and less error prone.

## Using the GUI client
The GUI is designed to be intuitive so does not need much explanation here. You should recognise the main 3 stages from above and be able to associate the relevant fields and actions. Some fields are auto-filled with suggested file paths, you can still choose to change them.

## Installing the GUI client
There are 3 versions of this client, each provides the same interface but are implemented differently which may be more or less compatible with your system.

### The windows .exe
If you can run this, then its probably the easiest option. The code is compiled into a standard windows `.exe` which you can double-click to run. The majority of the code runs directly from this `.exe`, however 1 part is still called separately and requires `java` (version 8 or 11) to be available. This is like the old client and is what implements stage 1.

### The linux binary
The python source code is compiled into a linux binary which you can run like any other application. The majority of the code runs directly from this binary, however 1 part is still called separately and requires `java` (version 8 or 11) to be available. This is like the old client and is what implements stage 1.

### The python source code
I have also provided the source version of the client which you can run if you have `python` installed. This also requires some python libraries, so I have provided an `install.sh` and `launch.sh` script to help implement what the application needs. This means you also need a bash-like environment (I will try to write `.bat` versions for windows cmd prompts). You also still need `java` for stage 1 to work.

# The CLI client
Each stage of the client process must be run as individual commands (multiple commands for interacting with the DWH's API) when using the Command Line Interface (CLI). This is simplest for development and keeping technical requirements as low as possible. If you would like to integrate the processing into an existing pipeline, this is the tool to use. However, many users find it tiring and error prone to use manually - in which case, you may prefer to try the [GUI client](#the-gui-client).

## Using the CLI client manually
Each stage has its own instructions. Some [installation/setup](#installing-the-cli-client) is required for some parts.
> __NOTE:__ Although I depict `.bat` scripts, they are not yet available, only `.sh` for bash-like shells
### Stage 1
> Ensure you have Java (version 8 or 11) installed
The java code is run by including the `.jar` libraries on the java classpath and asking java to run the specific class to perform the transformation. To make this a little easier, there is a script `stage1.bat` to help. You can call it from its directory and reference the data files with a longer path, or from the data directory and reference the script with a longer path. It requires the datasource.xml file and will output the fhir bunlde in xml to stdout, which can be redirected to a file. eg:
```bat
stage1.bat C:\Users\me\my\data\datasource.xml > C:\Users\me\my\data\client-output\fhir-bundle-RAW.xml
C:\Users\me\Downloads\dwh-client\stage1.bat datasource.xml > client-output\fhir-bundle-RAW.xml
```

### Stage 2
> Ensure you have python (version 3.7+) installed
This stage is backed by python and can more easily be run directly as python, without a wrapper script.
```bat
cat C:\Users\me\my\data\client-output\fhir-bundle-RAW.xml | python .\src\stream-pseudonymization.py > C:\Users\me\my\data\client-output\fhir-bundle-DWH.xml
cat client-output\fhir-bundle-RAW.xml | C:\Users\me\Downloads\dwh-client\src\stream-pseudonymization.py > client-output\fhir-bundle-DWH.xml
```
To avoid being promted for the `secret_key`, you could create a file (eg "_dwh-client.conf_") like this and load the key before running the above commands:
```
export secret_key="ChangeMe"
```
and load with:
```bat
. dwh-client.conf
```

### Stage 3
This part again runs as python and can be run directly:
```bat
python .\src\api_processing.py -u --name "MyData" --file C:\Users\me\my\data\client-output\fhir-bundle-dwh.xml
```
This uploads a bundle.

There are more parts to this stage, you can see all the available options with:
```bat
python .\src\api_processing.py --help
```
The most important part, which processes the uploaded data, is:
```bat
python .\src\api_processing.py -p --name "MyData"
```

Options:
* _list/summarize:_ Show overview/summary of the datasources for your user
* _info/error:_ Show info for most recent upload or error (if there are any)
* _upload:_ Upload a file with a fhir bundle of data
* _process:_ Integrate the uploaded data from file to database
* _delete:_ Remove the datasource (if it was created by your user)

## Installing the CLI client
The python code uses some libraries which aren't included. There is a helper script to install the libraries:
```bat
C:\Users\me\Downloads\cli-client\install.bat
```


# Developer notes
The project can be used as 3 separate "scripts" to perform each part, or using an interface to combine them which is more intuative for the user.

## The GUI
* Design in Qt Designer - a graphical tool for building Qt framework based interfaces.
* Convert to a python class with a command. 
* Code actions in window class inheriting from generated class.
* Reference the same code used for running individual "scripts".
* Package as python app (user will need python and to install libraries)
* Package as binary
    * Fat binary includes all dependencies
    * Normal binary requires dependencies from the user

Convert Qt designer's `.ui` file to python class:
```sh
## Must have pyside6-uic available (system package or pip)
pyside6-uic src/gui/mainWindow.ui -o src/gui/ui_mainwindow.py
```
Build the fat binaries with (from project root):
```sh
wine64 pyinstaller dwh_client.spec
pyinstaller dwh_client.spec
## Build .spec file with (eg. first run):
pyinstaller --onefile --add-data="resources:resources" --add-data="src:src" --add-data="src/gui/ui_mainwindow.py:src/gui/" --hidden-import=requests src/gui/dwh_client.py
```
