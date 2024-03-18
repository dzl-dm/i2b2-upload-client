<xsl:stylesheet version="2.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:fhir="http://hl7.org/fhir"
xmlns:f="CustomXSLTfns"
exclude-result-prefixes="f">
    <xsl:output method="xml" indent="yes"/>
    <xsl:strip-space elements="*"/>

    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <!-- Patient id logic -->
    <xsl:template match="fhir:Patient/fhir:identifier/fhir:value" >
      <xsl:copy>
        <xsl:attribute name="value">
            <xsl:value-of select="f:_hash_ids(
              string(../../fhir:name/fhir:given/@value),
              string(../../fhir:name/fhir:family/@value),
              string(../../fhir:birthDate//@value)
            )" />
        </xsl:attribute>
        <xsl:apply-templates select="@*|node()"/>
      </xsl:copy>
    </xsl:template>
    <!-- Apply template to id attribute of patients -->
    <xsl:template match="fhir:Patient/fhir:identifier/fhir:value/@value" />

    <!-- Remove name elements -->
    <xsl:template match="fhir:Patient/fhir:name"/>

    <!-- Encounter id logic -->
    <xsl:template match="fhir:resource/fhir:Encounter/fhir:identifier/fhir:value" >
      <xsl:copy>
        <xsl:attribute name="value">
            <xsl:value-of select="../../fhir:id/@value" />
          </xsl:attribute>
        <xsl:apply-templates select="@*|node()"/>
      </xsl:copy>
    </xsl:template>
    <!-- Apply template to id attribute of encounter -->
    <xsl:template match="fhir:resource/fhir:Encounter/fhir:identifier/fhir:value/@value" />

    <!-- Remove comments -->
    <xsl:template match="comment()"/>

</xsl:stylesheet>
