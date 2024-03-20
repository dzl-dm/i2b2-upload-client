# i2b2 upload client
Utilising a helper file, which uses a custom XML format to define meanings, this application will convert CSV based patient data into fhir-xml format. This is helpful for integrating diverse sources of date into a standardised format for furhter analysis.

## Helper file
We usually call this the `datasource.xml`. Its a custom xml definition of how the csv patient data is formatted (which files, which columns map to which parameters).

## Running the application
The initial aim is to allow the upload process to be run with low effort. This will evolve into a client with few dependencies and high ease of use - after enough development.

### Docker mode
Ensure you have docker installed (eg [docker desktop](https://docs.docker.com/desktop/install/windows-install/)) - [wsl2](https://learn.microsoft.com/en-us/windows/wsl/install) is an advisable pre-requisite to docker on windows for performance.
Then start the DWH image as a local container with:
```sh
docker run --name local-dwh-client --rm -it -v my/local/datasources:/datasources -e log_verbosity=1 -e secret_key="ChangeMe" -e dwh_api_key="ChangeMe" ghcr.io/dzl-dm/i2b2-upload-client/i2b2-dwh-client
```
It will run interactively by offering you options for how to proceed.

The `-v my/local/datasources:/datasources` maps the left side on your local filesystem to the right side within docker and will need to contain your datasources in this structure:
ds1/datasource.xml
ds2/datasource.xml
dsN/datasource.xml
> NOTE: Under windows, the left side must be be an absolute path, eg C:\Users\me\datasources

The `datasource.xml` references csv files with data for patients, visits and observations. These references will be respected as previously, it may be necessary to adjust path separators from backslash to forward slash.

The processing only adds or overwrites data in a sub-directory for each datasource called `client-output`, no other data is changed.

## How it works
There are 3 stages to the process which are handled by this client.
1. Converting to fhir
1. pseudonymising
1. uploading

This doesn't map exactly to ETL (Extract, Transform, Load) as extraction is a pre-requisite; the csv patient data is already extracted. So these cover most of the transformation part, however further trasnformation is required on the server side before loading (server side) into the i2b2 database.

### Convert to fhir
Once you have clean data in csv files and a matching helper-file (datasource.xml), the following command will produce the data in fhir-xml:
```sh
i2b2-client-fhir datasource.xml > fhir-data-raw.xml
```
At this stage, the data content is unchanged, but re-formatted. Identifiable data will remain until the next stage.

> NOTE: This stage requires `java 11` - more recent versions of java have removed a feature which this code relies on

### Pseudonymise
Here we create a pseudonym for each patient and remove the name information from the data. Comments are also removed from the fhir data as they could hold sensitive information. Each client will generate different pseudonyms for the same patient due to a locally generated secret key. You should aim to keep a backup of the secret key you're using (perhaps in a password manager) to ensure you can always use the same key:
```sh
./process-pid.py
```
The output is still a fhir bundle in XML format, simply with the changes outlined above.

> NOTE: This stage requires `python 3`

### Upload
The DWH presents an API which the client can interface with. A simple way to interact with the API is to use cURL, but most programming languages offer a network library which could be used to communicate.

> NOTE: This stage requires the cURL command to be available, which is included in `git for windows`
