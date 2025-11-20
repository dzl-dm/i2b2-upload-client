# i2b2 upload client
This software helps you upload data collected in medical registers, studies and trials to a centralized Data Warehouse, which can be queried for discovery of relevant data and Bio-Material for further research.

## The Goal
Enable your data to be searched using canonical terms (defined in the DZL's Meta Data Repository, [CoMetaR](https://data.dzl.de/cometar/#/)). The search doesn't allow patient identification or some very granular or complex queries. The primary purpose is to democratize visibility and discovery of the data and samples through feasibility queries. Access to actual data will require further steps with the local data manager to each site who must ensure the data and samples may be shared. The DZL must also be informed of publications being made which utilize DZL funded data/sample collection.

## Preparing the data
The DZL DWH has certain structure/format requirements for data to be uploaded, which is split into 2 stages. Ultimately, the data must be uploaded with pseudonymized patients and canonicalized data as an XML FHIR Bundle containing Patient, Encounter and Observation resources. The pseudonymization and conversion to FHIR can be handled by our upload client in the [uploading the data](#uploading-the-data) stage, but that process also requires well formatted data and a mapping file, usually named `datasource.xml`.

The broad principals:  

* Separate Patients, Visits, Observations  
* Observations can be in long/EAV format or wide format (you can provide multiple observation files, each in different formats)  
* Using wide format can handle `modifiers` better  
    * Modifiers can be seen highlighted green in [CoMetaR](https://data.dzl.de/cometar/#/), they provide supporting information to a concept  

Because each project/datasource will deliver their data in various formats, pre-processing or transformation of the data needs to be done uniqely for each. We often use `Rscript`s to solve these problems, though it is not a perfect, repeatable process and other tools can be used at this stage, you must read on and understand the rest of the process to know what the target format is here.

When everything runs correctly, you will have created some `.csv` files matching the 1st broad princpal above (patients, visits, observations). You can now ensure your mapping file, `datasource.xml`, looks correct.

You can find examples of the `datasource.xml` [here](https://github.com/rwm/histream/tree/master/histream-import/src/test/resources). If you need further help, please get in contact with [central data management](https://dzl.de/en/platforms/contact-central-data-management/)

Once you are happy with the csv and mapping files, you can move on to uploading data.

## Uploading the data
This part converts the tabular data (csv files) into XML, pseudonymizes patient identifiable data and communicates with the DZL DWH server to upload and integrate the data.

The `i2b2-upload-client`, this project, helps you do all of these tasks, you can download from the [github project](https://github.com/dzl-dm/i2b2-upload-client/releases)'s releases. Primarily, I recommend the graphical version (`dwh client.exe` for Windows users, `dwh client` for linux/mac users) which should contain all the technical components required to run. The other options may be useful if you would like to automate the process and integrate into scripts. I will describe the GUI usage here.

Requirements:  

* An API key from DZL Central Data Management team  
* A salt/pseudonym-key which you generate yourself  

When you open the client, the window will have 2 tabs at the top, `Local processing` and `DWH processing`. You would usually use them left to right. So starting with Local processing, Stage 1 will ingest all the data and mapping you created earlier and produce an XML file with the raw fhir data. You must select the `datasource.xml` file and ensure its internal references to data files are correct (eg, copy/link it to the correct directory). The client will try to auto-populate as many of the other text boxes as possible, so you should be able to "Generate Fhir bundle" after selecting just that one file.

The next stage will pseudonymize the patient data. Even if you already use pseudonyms, this stage can be applied. It also removes certain fields from the xml fhir bundle which are not required. You must supply and "Pseudonymization key" or salt, which is used to hash the patient data. This salt is like a password, it allows the hash to remain deterministic, but only to those knowing the salt (so you, and only you, can re-identify patient id's - this becomes relevant when DWH users request data from you).

The data is now ready, so the final phase is uploading and integrating to the DWH - this happens in the "DWH processing" tab. The 1st textbox should be pre-filled with the API URL (https://data.dzl.de/api), please enter your API key in the 2nd text box at the top and press "Connect...". If it worked, the button will turn green.

Now, the datasource file refers to the XML FHIR Bundle generated and pseudonymized in "Local processing", it'll be pre-filled with the default (if you have been through stages 1 and 2), so you only need to change it if that doesn't fit for you.

The main drop-down menu lets you see each datasource which you manage, if you're updating an existing source, ensure you select it here - That will also update the datasource text-box. You can use the "Show info" and "Show errors" buttons to see some more details about the existing upload, or use the "Delete source" button to remove it from the DWH.

Uploading a new source works the same way as updating an existing source. They will overwrite the datasource corresponding to the datasource name textbox. When you press "Upload", the FHIR Bundle is sent to the server, using compression if needed. Once this has finished (you may need to press "Reload status" to check), you must still press "Update source", which tells the server to integrate the new data into the DWH. This can take some time, so you will want to press the "Reload status" button again to keep checking.

If everything worked, the server will run some further processing to optimize the query tool, but from your point of view, the process is complete.

## How it works
This application uses 3 components to upload patient data to a Data Warehouse. To use the application, you do not need to have a technical understanding of each part, they are however visible as a user so you must be aware of the broad process and what is required of you at each stage. Each stage can be run independently from the other.

1. Convert CSV data into standardized a FHIR bundle in XML format
1. Pseudonymize the identifiable data (if it isn't already)
1. Upload to the DWH and manage the status of the data

### Stage 1 - FHIR conversion
For each dataset you want to upload, you need the data (already transformed into csv files) and a `datasource.xml` configuration file, which maps the csv data to standard, internationally recognised concept codes. This is the same as with the previous client, however, we need to add an extra XML tag for timezone within the "\<meta\>" element.
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datasource version="1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<meta>
		<id>...</id>
		<etl-strategy>...</etl-strategy>
		<version-date>...</version-date>
		<timezone>Europe/Berlin</timezone> <!-- ADD THIS LINE -->
	</meta>
...
</datasource>
```
A java program uses the XML configuration to convert the data into a fhir bundle in XML.

> __NOTE:__ Further example data and `datasource.xml` files can be found in the [HiStream project](https://github.com/rwm/histream/tree/master/histream-import/src/test/resources)

### Stage 2 - Pseudonymization
Data protection is very important, so this stage removes the name information and creates a non-reversible (but still deterministic) ID as the pseudonym for the patient. You must provide a `secret key` (a long, random string you generate yourself and keep secret) so that only you generate the pseudonym for the patients. If someone else were to run this stage with their secret key, it would not produce compatible pseudonyms. Record linkage can be achieved by sharing the secret key. This makes sense in environments where multiple people manage different parts of the same data set. Since client version v0.1.1, we also write a `psn-cache.tsv` file which helps you to re-identify patients upon request.
> NOTE: If you already use pseudonyms, we don't require that you also use our pseudonymisation process (although it doesn't hurt). Once your data is uploaded, personal information such as patient name is not used. We remove this client-side during pseudonymization, but don't _yet_ provide an option to remove it without also generating new pseudonyms.

### Stage 3 - Upload and DWH management
In the base upload case, this is a two part process, where you must trigger each part manaully:

* Upload - Send the FHIR data
* Process - Integrate into the DWH database

You can add, update and delete the data in this stage. You must provide your `API key` (will be provided to you when you are invited to use the upload system). You can also view the status of each source that you have already added to the DWH.

### Summary
What you need to make an upload:

* Transformed data as `.csv` file(s)
* Compatible `datasource.xml`
* A self generated `secret_key` also called `Pseudonymization key`
* A provided `dwh_api_key` also called `API key`
* A working upload client (graphical or command line). Requires:
	* Java v8 or v11
	* Python v3.7+

# The GUI client
I have developed a Graphical User Interface (GUI) which uses the same background code as the [command line client](#the-cli-client). It "simply" adds a visual interface to make the process more intuitive and less error prone.

## Using the GUI client
The GUI is designed to be intuitive so does not need much explanation here (and is explained above). You should recognise the main 3 stages from above and be able to associate the relevant fields and actions. Some fields are auto-filled with expected file paths, you can still choose to change them.

## Installing the GUI client
There are 3 versions of this client, each provides the same interface but are implemented differently which may be more or less compatible with your system.

### The windows .exe
If you can run this, then its probably the easiest option. The code is compiled into a standard windows `.exe` which you can double-click to run. The majority of the code runs directly from this `.exe`, however 1 part is still called separately and requires `java` (version 8 or 11) to be available. This is like the old client and is what implements stage 1.

#### Autofill for windows
Its possible to define variables in a file so you don't have to fill them in each time you use the application, here I show you how. Create a file (any name and location you like, but with the extension `.bat`). eg. `launch-dwh-client.bat` with content:
```
set secret_key=ChangeMe
set dwh_api_key=ChangeMe
call drive:\path\to\dwh_client.exe
```
Where the last line should support the env variable. E.g. `$env:USERPROFILE\dzl\dwh_client.exe`
Then this can be executed or called from the cmd console with:
```
call launch-dwh-client.bat
```

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



# Manual CLI mode (eg for automation)
This is as raw as it gets, there are no helper scripts for each stage, just the direct commands. It has the fewest dependencies, but you must setup everything manually. You should be able to follow the (Client setup)[#Client-setup] part once, then be able to run the stages directly any time.

## Client setup
We need to set the following 2 keys for the client to use when you open a new cmd/shell to use the client.
```
## Windows:
set secret_key=""
set dwh_api_key=""
## Linux
export secret_key=""
export dwh_api_key=""
```
> You will be provided with the `dwh_api_key` when you are granted access to upload data to the DWH.

> You should generate the `secret_key` as a long random string (like a password). Use the same one for all datasets unless you want to remove the possibility of record linkage between datasets. Share the key only when someone else is also managing complimentary data for the same patients (eg observational data and biobank data)

> __Note for Windows:__ From my experience, the `set` command only works in an admin cmd window. This application has no requirement for admin privileges. It seems also possible to use a different syntax under powershell. eg for __secret_key__: `[Environment]::SetEnvironmentVariable("secret_key", "ChangeMe", "User")` where "User" is literal, not the username.

We also need to install python libraries:
```
pip install -r /path/to/cli-client/src/requirements.txt
```
> Using venv or similar tools is beyond the scope of this readme

## Per-dataset preparation
For each dataset you want to upload, you need the data (already transformed into csv files) and a `datasource.xml` configuration file. Please ensure it is adapted as described in [Stage 1: FHIR conversion](#stage-1---fhir-conversion)

The processing stages will use intermediate files which can safely be deleted after the upload. You can choose what to call them:

* Stage 1 output: A FHIR bundle of the whole dataset in XML format (eg `fhir_raw.xml`)
* Stage 2 output: Pseudonymize the existing patient identifying data in the fhir_raw.xml (eg `fhir_dwh.xml`)

## Stage 1:
You must use java version 8 (1.8) or 11. Check with `java -version`. You can have multiple versions installed, you may need to research how to run a specific version on your system (and potentially replace the initial `java` command below with the specific, desired java version).
```sh
## Windows
java -Dfile.encoding="UTF-8" -cp "$env:USERPROFILE\dzl\cli-client\lib\*" de.sekmi.histream.etl.ExportFHIR datasource.xml > output-fhir_raw.xml
## Linux
java -Dfile.encoding="UTF-8" -cp /path/to/cli-client/lib/\* de.sekmi.histream.etl.ExportFHIR ./datasource.xml > output-fhir_raw.xml
```

## Stage 2:
```sh
## Windows
type output-fhir_raw.xml | /path/to/cli-client/src/stream_pseudonymization.py > output-fhir_dwh.xml
## Linux
cat output-fhir_raw.xml | /path/to/cli-client/src/stream_pseudonymization.py > output-fhir_dwh.xml
```
> __NOTE:__ Depending on your environment, you may need to prefix the python script with your python executable. Under windows, this is often `py`. eg `
type output-fhir_raw.xml | py /path/to/cli-client/src/stream_pseudonymization.py > output-fhir_dwh.xml
`

## Stage 3:
Stage 3 encompases all the interactions with the DWH API. There are multiple things you can do, 2 at minimum are vital to upload data.
### Part a:
```sh
## Upload
/path/to/cli-client/src/api_processing.py -u -n "My Source Name" -f ./output-fhir_dwh.xml
```

### Part b:
```sh
## Process
/path/to/cli-client/src/api_processing.py -p -n "My Source Name"
```
> At this point, if there weren't any errors, the data is uploaded and available in the Data Warehouse. You can use some of the following guidance to view more information and delete the data from the Data Warehouse.

> __NOTE:__ The `api_processing.py` command demands interactive confirmation of changes to the database (_part b_ processes the changes, so will update the database. Deleting a datasource would also require confirmation). For automation, I have added a `-y` flag (for "yes"). If this is added to the _part b_ command, it will no longer prompt for confirmation.

## View and manage data sources
Information on how to get more from the Data Warehouse's API. List all sources, view status and details about each source, delete sources.
```sh
## View the help page of the client 
/path/to/cli-client/src/api_processing.py --help
## View a summary list of all sources in the DWH
/path/to/cli-client/src/api_processing.py -S
## View status of a single source in the DWH
/path/to/cli-client/src/api_processing.py -s -n "My Source Name"
## View info or error of a single source in the DWH
/path/to/cli-client/src/api_processing.py -i -n "My Source Name"
/path/to/cli-client/src/api_processing.py -e -n "My Source Name"
## Delete a single source in the DWH
/path/to/cli-client/src/api_processing.py -d -n "My Source Name"
```

## Developer/contributions
I'm a developer, how do I run/test and contribute to the project?

Aside from python and the libraries imported and used inside the code, this project also uses `uv` as the build frontend and optionally the backend. You can keep using `pip`, but its not recommended, especially to ensure dependencies are corerctly defined. The project also uses `QT-Designer`, which is a GUI application to help design GUI's. This produces `.ui` files which then need converting to python with the `uic` tool. If you're not making GUI changes, you don't need this tool.

To run the application locally:
```sh
## With uv:
uv sync
uv run [--no-project] src/gui/dwh_client.py
## With pip:
python -m venv .venv
. .venv/bin/activate
pip install .
python src/gui/dwh_client.py
deactivate
```

To build the GUI from `.ui` file
```sh
## You need to install pyside6-tools for the command `pyside6-uic`
pyside6-uic src/gui/mainWindow.ui -o src/gui/ui_mainwindow.py
```

Build executables (should take ~45 seconds and produce executables of ~100mb)
```sh
## Relies on this once first:
uv add --dev pyinstaller
## Then each time:
uv run pyinstaller dwh_client.spec
## And for windows:
uv run wine pyinstaller dwh_client.spec
```
