# i2b2 upload client
Utilising a helper file, which uses a custom XML format to define meanings, this application will convert CSV based patient data into fhir-xml format. This is helpful for integrating diverse sources of date into a standardised format for furhter analysis.

## Helper file
We usually call this the `datasource.xml`. Its a custom xml definition of how the csv patient data is formatted (which files, which columns map to which parameters).

## Running the application
The initial aim is to allow the upload process to be run with low effort. This will evolve into a client with few dependencies and high ease of use - after enough development.

### Docker mode
Ensure you have docker installed (docker desktop is fine) and start the DWH image as a local container with:
```sh
docker run --name local-dwh-client --rm -it -v my/local/datasources:/datasources -e log_verbosity=3 -e secret_key="ChangeMe" dwh_api_key="ChangeMe" i2b2-upload-client
```

It will run interactively by offering you options for how to proceed.

## How it works
There are 3 stages to the process.
1. Converting to fhir
1. pseudonymising
1. uploading

This doesn't map exactly to ETL as extraction is a pre-requisite, the csv patient data is already extracted. So these cover most of the transformation part, however further trasnformation is required on the server side before loading into the i2b2 database.

### Convert to fhir
Once you have clean data in csv files and a matching helper-file, the following command will produce the data in fhir-xml:
```sh
i2b2-client-fhir -d datasource.xml > fhir-data.xml
```
At this stage, the data is unchanged, but re-formatted. Identifiable data will remain until the next stage.

### Pseudonymise
Here we create a pseudonym for each patient and remove the name information from the data. Comments are also removed from the fhir data as it could hold sensitive information. Each client will generate different pseudonyms for the same patient due to a locally generated secret key. If you are migrating your environment and want to keep patient pseudonym compatibility, keep a backup of your secret key - more details on that topic below:
```sh
./process-pid.py
```
The output is still a fhir bundle in XML format, simply with the changes outlined above.

### Upload
The DWH should present an API which the client can interface with. A simple way to interact with the API is to use cURL, but most programming languages offer a network library which could be used to communicate.
