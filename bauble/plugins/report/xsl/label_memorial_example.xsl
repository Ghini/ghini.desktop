<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:abcd="http://www.tdwg.org/schemas/abcd/2.06"
  version="1.0"
  >
  <xsl:template match="abcd:DataSets">
    <!-- set a global font family here, always available are Courier, Halvetica, Times -->
    <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format" font-family="Courier">


      <!-- PAGE -->
      <fo:layout-master-set>
        <fo:simple-page-master
          master-name="A4"
          page-height="210mm"
          page-width="297mm"
          margin-top="5mm"
          margin-bottom="5mm"
          margin-left="5mm"
          margin-right="5mm"
          >
          <fo:region-body column-count="2" column-gap="0" />
        </fo:simple-page-master>
      </fo:layout-master-set>
      <fo:page-sequence master-reference="A4">
        <fo:flow flow-name="xsl-region-body">
          <xsl:for-each select="abcd:DataSet">
            <xsl:for-each select=".//abcd:Unit">


              <!-- FULL BOTANIC NAME -->
              <!-- we construct the full name in a variable so we can check it to get a font size -->
              <xsl:variable name="full-botanic-name">
                <!-- GENUS -->
                <!--  ID Qualifier, if present at genus level -->
                <xsl:if test=".//abcd:IdentificationQualifier[@insertionpoint='genus']">
                  <fo:inline font-style="normal">
                    <xsl:choose>
                      <xsl:when test=".//abcd:IdentificationQualifier = 'incorrect'">
                        <xsl:text>(incorrect)</xsl:text>
                      </xsl:when>
                      <xsl:otherwise><xsl:value-of select=".//abcd:IdentificationQualifier"/></xsl:otherwise>
                    </xsl:choose>
                    <xsl:if test=".//abcd:IdentificationQualifier != '?'"><xsl:text> </xsl:text></xsl:if>
                  </fo:inline>
                </xsl:if>
                <xsl:choose>
                  <!-- Check for botanist tag Genus name by looking for 3 capital letters at start -->
                  <xsl:when test="starts-with(translate(.//abcd:GenusOrMonomial,
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    'XXXXXXXXXXXXXXXXXXXXXXXXXX'), 'XXX')">
                    <fo:inline font-style="normal">
                      <xsl:value-of select=".//abcd:GenusOrMonomial" />
                    </fo:inline>
                  </xsl:when>
                  <!-- Check for nothogenus -->
                  <xsl:when test="starts-with(.//abcd:GenusOrMonomial, 'x')">
                    <fo:inline font-style="normal"><xsl:text>×</xsl:text></fo:inline>
                    <xsl:value-of select="substring(.//abcd:GenusOrMonomial,2)"/>
                  </xsl:when>
                  <!-- For normal genus -->
                  <xsl:otherwise>
                    <xsl:value-of select=".//abcd:GenusOrMonomial" />
                  </xsl:otherwise>
                </xsl:choose>
                <!-- SPECIES -->
                <!-- first check if the field is in use -->
                <xsl:if test=".//abcd:FirstEpithet != ''">
                  <xsl:text> </xsl:text>
                  <!--  ID Qualifier, if present at species level -->
                  <xsl:if test=".//abcd:IdentificationQualifier[@insertionpoint='sp']">
                    <fo:inline font-style="normal">
                      <xsl:value-of select=".//abcd:IdentificationQualifier"/>
                      <xsl:if test=".//abcd:IdentificationQualifier != '?'"><xsl:text> </xsl:text></xsl:if>
                    </fo:inline>
                  </xsl:if>
                  <xsl:choose>
                    <!-- Check for "sp." -->
                    <xsl:when test="starts-with(.//abcd:FirstEpithet, 'sp.')">
                      <fo:inline font-style="normal">
                        <xsl:value-of select=".//abcd:FirstEpithet"/>
                      </fo:inline>
                    </xsl:when>
                    <xsl:otherwise>
                      <!-- for nothotaxon hybrid with flag -->
                      <xsl:value-of select=".//abcd:HybridFlag"/>
                      <xsl:value-of select=".//abcd:FirstEpithet"/>
                    </xsl:otherwise>
                  </xsl:choose>
                </xsl:if>
                <!-- RANK -->
                <!--  ID Qualifier, if present at infraspecific rank level -->
                <xsl:if test=".//abcd:Rank != ''">
                  <xsl:text> </xsl:text>
                  <xsl:if test=".//abcd:IdentificationQualifier[@insertionpoint='infrasp']">
                    <fo:inline font-style="normal">
                      <xsl:value-of select=".//abcd:IdentificationQualifier"/>
                      <xsl:if test=".//abcd:IdentificationQualifier != '?'"><xsl:text> </xsl:text></xsl:if>
                    </fo:inline>
                  </xsl:if>
                  <fo:inline font-style="normal">
                    <xsl:value-of select=".//abcd:Rank"/>
                  </fo:inline>
                </xsl:if>
                <!-- INFRASPECIFIC EPITHET -->
                <xsl:if test=".//abcd:InfraspecificEpithet != ''">
                  <xsl:text> </xsl:text>
                  <xsl:choose>
                    <xsl:when test=".//abcd:Rank != ''">
                      <xsl:value-of select=".//abcd:InfraspecificEpithet"/>
                    </xsl:when>
                    <xsl:otherwise>
                      <fo:inline font-style="normal">
                        <xsl:value-of select=".//abcd:InfraspecificEpithet"/>
                      </fo:inline>
                    </xsl:otherwise>
                  </xsl:choose>
                </xsl:if>
                <!-- CULTIVAR -->
                <xsl:if test=".//abcd:CultivarName != ''">
                  <fo:inline font-style="normal">
                    <xsl:text> </xsl:text>
                    <xsl:value-of select=".//abcd:CultivarName"/>
                  </fo:inline>
                </xsl:if>
              </xsl:variable>

              <!-- SET FONTS SIZE FOR BOTANIC NAME -->

              <!-- calculate the length of the botanic name -->
              <xsl:variable name="bot-name-length">
                <xsl:value-of select="string-length($full-botanic-name)"/>
              </xsl:variable>
              <!-- double up capitals and w and m to represent true width -->
              <xsl:variable name="bot-name-extra-space">
                <xsl:value-of select="$bot-name-length - string-length(translate(string($full-botanic-name), 'wmABCDEFGHIJKLMNOPQRSTUVWXYZ', ''))"/>
              </xsl:variable>
              <xsl:variable name="bot-name-total-length" select="$bot-name-length + $bot-name-extra-space"/>

              <!-- calculate the font size -->
              <xsl:variable name="bot-name-font-size">
                <!-- set some conditions that determine the font size -->
                <xsl:choose>
                  <!-- Test if the first or last lines worth of chars contain any spaces/linebreaks -->
                  <xsl:when test="string-length(substring-before(string($full-botanic-name), ' ')) &gt; 24 or
                    not(contains(substring(string($full-botanic-name), string-length(string($full-botanic-name)) - 24), ' '))">
                    <xsl:value-of select="'22pt'"/>
                  </xsl:when>
                  <!-- Test if the longer names have any spaces/linebreaks in the middle -->
                  <xsl:when test="$bot-name-total-length &gt; 33 and not(contains(substring(string($full-botanic-name), 19, 8), ' '))">
                    <xsl:value-of select="'24pt'"/>
                  </xsl:when>
                  <!-- Test for extra long names -->
                  <xsl:when test="$bot-name-total-length &gt; 47">
                    <xsl:value-of select="'22pt'"/>
                  </xsl:when>
                  <!-- Test for long names -->
                  <xsl:when test="$bot-name-total-length &gt; 45">
                    <xsl:value-of select="'24pt'"/>
                  </xsl:when>
                  <!-- Normal: failing any of the above tests set the font to normal size -->
                  <xsl:otherwise><xsl:value-of select="'26pt'"/></xsl:otherwise>
                </xsl:choose>
              </xsl:variable>



              <!-- LABEL BLOCK -->

              <fo:block-container
                margin=".5mm"
                keep-together.within-column="always"
                border="solid black 1px"
                width="140mm"
                height="80mm"
                >

                <!-- LOGOS -->
                <!-- put first so other blocks overlap it. -->

                <fo:block-container
                  absolute-position="absolute"
                  top="51mm"
                  margin-right="3mm"
                  text-align="right"
                  line-height="0pt"
                  font-size="0pt"
                  >
                  <fo:block>
                    <fo:external-graphic
                      src="logo.png"
                      content-height="scale-to-fit"
                      height="14mm"
                      >
                    </fo:external-graphic>
                  </fo:block>
                </fo:block-container>

                <fo:block-container
                  absolute-position="absolute"
                  top="4mm"
                  margin-right="3mm"
                  text-align="right"
                  line-height="0pt"
                  font-size="0pt"
                  >
                  <fo:block
                    text-align="right">
                    <fo:external-graphic
                      src="memorial_logo.svg"
                      content-height="scale-to-fit"
                      height="24mm"
                      >
                    </fo:external-graphic>
                  </fo:block>
                </fo:block-container>


                <!-- MEMORIAL TREE INFO -->

                <xsl:if test="Notes">
                  <fo:block-container absolute-position="absolute"
                    top="6mm"
                    bottom="35mm">
                    <!--tree number -->
                    <xsl:for-each select="Notes">
                      <fo:block
                        font-size="18pt"
                        font-family="Helvetica"
                        font-weight="bold"
                        margin-left="4mm"
                        margin-right="40mm"
                        text-align="left">
                        <xsl:text>Tree No. </xsl:text>
                        <xsl:value-of select=".//memorial_tree_no" />
                      </fo:block>
                      <!-- name -->
                      <fo:block
                        font-size="18pt"
                        font-family="Helvetica"
                        font-weight="bold"
                        margin-left="4mm"
                        margin-right="40mm"
                        text-align="left">
                        <xsl:value-of select=".//memorial_name" />
                      </fo:block>
                    </xsl:for-each>
                  </fo:block-container>
                </xsl:if>

                <!-- BOTANIC NAME -->

                <fo:block-container
                  absolute-position="absolute"
                  top="29mm"
                  height="31mm"
                  >
                  <!-- here is where the fontSize variable is used-->
                  <fo:block
                    font-size="{$bot-name-font-size}"
                    font-style="italic"
                    font-weight="bold"
                    margin-left="4mm"
                    margin-right="4mm"
                    text-align="left"
                    >
                    <xsl:copy-of select="$full-botanic-name" />
                  </fo:block>
                </fo:block-container>

                <!-- COMMON NAME -->

                <fo:block-container
                  absolute-position="absolute"
                  top="60mm"
                  right="30mm"
                  left="4mm"
                  height="7.5mm"
                  >
                  <fo:block
                    font-weight="400"
                    font-size="17pt"
                    text-align="left"
                    >
                    <xsl:value-of select=".//abcd:InformalNameString" />
                  </fo:block>
                </fo:block-container>

                <!-- divide line -->

                <fo:block-container
                  absolute-position="absolute"
                  top="67.5mm"
                  height="1mm"
                  left="4mm"
                  right="4mm"
                  >
                  <fo:block
                    border-bottom-width="2pt"
                    border-bottom-style="solid"
                    border-bottom-color="black"
                    >
                  </fo:block>
                </fo:block-container>

                <!-- FAMILY -->

                <!-- Should check for HigherTaxon = familia -->
                <fo:block-container
                  absolute-position="absolute"
                  top="69mm"
                  left="4mm"
                  right="60mm"
                  height="8mm"
                  >
                  <fo:block
                    font-size="17pt"
                    font-weight="bold"
                    text-align="left"
                    >
                    <xsl:if test=".//abcd:HigherTaxonRank = 'familia'">
                      <fo:inline font-style="normal">
                        <xsl:value-of select=".//abcd:HigherTaxonName" />
                      </fo:inline>
                    </xsl:if>
                  </fo:block>
                </fo:block-container>

                <!-- LABEL DISTRIBUTION -->

                <fo:block-container
                  absolute-position="absolute"
                  top="69mm"
                  right="4mm"
                  left="60mm"
                  height="8mm"
                  >
                  <fo:block
                    font-size="13pt"
                    text-align="right"
                    >
                    <xsl:value-of select="distribution" />
                  </fo:block>
                </fo:block-container>
              </fo:block-container>
            </xsl:for-each>
          </xsl:for-each>
        </fo:flow>
      </fo:page-sequence>
    </fo:root>
  </xsl:template>
</xsl:stylesheet>
