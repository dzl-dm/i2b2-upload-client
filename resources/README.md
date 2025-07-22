# Resources

We also make use of the (Hi-Stream)[https://github.com/rwm/histream] project. To develop and build this project, you should include some of the `.jar` libraries (don't upload them to this git project!) both directly from the Hi-Stream project and its dependencies. Fetch them like this:
```sh
mkdir -p resources/lib
cd resources/lib
wget https://repo1.maven.org/maven2/javax/activation/activation/1.1.1/activation-1.1.1.jar
wget https://repo1.maven.org/maven2/javax/xml/bind/jaxb-api/2.3.1/jaxb-api-2.3.1.jar
wget https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-core/2.3.0.1/jaxb-core-2.3.0.1.jar
wget https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-impl/2.3.2/jaxb-impl-2.3.2.jar
## Check with developer for most up-to-date versions, not available through maven.org
## Not available on Maven: histream-common-0.17-SNAPSHOT.jar
wget https://repo1.maven.org/maven2/de/sekmi/histream/histream-js/0.13.3/histream-js-0.13.3.jar
wget https://repo1.maven.org/maven2/de/sekmi/histream/histream-import/0.13.3/histream-import-0.13.3.jar
```
