## An image to run locally which encapsulates the DWH upload components
    # FHIR conversion
    # Pseudonymisation (of the FHIR data)
    # Upload to and interaction with the DWH

## NOTE when BUILDing: "context" should be parent of this "docker" directory

## We need both java and python, so we simply install them on top of a base system
# FROM debian:stable-slim
## We need an older java version - either older or fatter debian image needed
FROM debian:11-slim 

ENV TZ=${TZ:-'Europe/Berlin'}

## Prepare the system for the applications
ARG DEBIAN_FRONTEND="noninteractive"
RUN apt-get update && \
    apt-get -y install \
    default-jdk \
    python3 \
    python3-pip \
    tzdata \
    && \
    apt-get autoremove -y

WORKDIR /upload-client

## Java fhir client is simply a fetched resource and won't change often, so we'll install that first
## TODO: Upload "package" to github and pull from there
COPY ./resources/lib ./fhir-transform/lib
COPY --chmod=0755 ./docker/process_data.sh ./fhir-transform/process_data.sh

## Pre-requisites
# For python pseudonymisation
COPY ./src/requirements.txt ./pseudonym/requirements.txt
# RUN pip install --break-system-packages --no-cache-dir -r ./pseudonym/requirements.txt
RUN pip install --no-cache-dir -r ./pseudonym/requirements.txt

## Full install
# For python pseudonymisation
COPY --chmod=0755 ./src/process-pid.py ./pseudonym/src/process-pid.py
COPY --chmod=0644 ./resources/fhir_both-python.xslt ./pseudonym/resources/fhir_both-python.xslt

# For uploader
ENV DWH_API_ENDPOINT=http://localhost:8000/
COPY --chmod=0755 ./docker/api-interaction.sh ./upload/api-interaction.sh

# ...and overall coordination
ENV log_verbosity=1
VOLUME /datasources/
COPY --chmod=0755 ./docker/coordinate_data_processing.sh ./coordinate_data_processing.sh

## The coordination script will handle what it can locally alone, then become interactive so the user can drive
CMD ["./coordinate_data_processing.sh"]
