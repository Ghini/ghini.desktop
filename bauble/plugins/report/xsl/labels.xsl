<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:fo="http://www.w3.org/1999/XSL/Format"
		xmlns:abcd="http://www.tdwg.org/schemas/abcd/2.06"
		version="1.0">

  <xsl:template match="abcd:DataSets">
    <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">

      <fo:layout-master-set>
	<fo:simple-page-master master-name="letter"
			       page-height="8.5in"
			       page-width="11in"
			       margin-top="0.5in"
			       margin-bottom="0.5in"
			       margin-left="0.5in"
			       margin-right="0.5in">
	  <fo:region-body column-count="2" column-gap="0" />
	</fo:simple-page-master>
      </fo:layout-master-set>

      <fo:page-sequence master-reference="letter">
	<fo:flow flow-name="xsl-region-body">
	  <xsl:for-each select="abcd:DataSet">
	    <xsl:for-each select=".//abcd:Unit">

	      <!-- ** the label block ** -->
	      <fo:block-container margin=".5mm"
				  keep-together="always"
				  border="solid black 1px"
				  width="122mm"
				  height="59mm">

		<!-- ** Family ** -->
		<!--  TODO: should only select the family name if the
		     HigherTaxonRank is familia -->
		<fo:block-container absolute-position="absolute"
				    top="4mm" bottom="29mm">
		  <!-- border="solid yellow 1px" -->
		  <fo:block font-family="sans"			    
			    font-weight="bold"
			    margin-left="5mm"
			    margin-right="5mm"
			    font-size="20pt"
			    text-align="center">
		    <xsl:value-of select=".//abcd:HigherTaxonName" />
		  </fo:block>
		</fo:block-container>

		<!-- ** Scientific name ** -->
		<!-- TODO: this isn"t properly setting the name to italics,
		     maybe it"s a problem with XEP -->
		<!-- border="solid red 1px" -->
		<fo:block-container absolute-position="absolute"
				    display-align="center"
				    top="14mm"
				    bottom="26mm">
		  <fo:block line-height=".9"
			    font-size="23pt"
			    font-family="serif"
			    font-style="italic"
			    font-weight="500"
			    margin-left="2mm"
			    margin-right="2mm"
			    text-align="center">
		    <xsl:value-of select=".//abcd:FullScientificNameString" />
		  </fo:block>
		</fo:block-container>

		<!-- ** Vernacular name ** -->
		<!-- border="solid green 1px" -->
		<fo:block-container absolute-position="absolute"
				    top="33mm"	    
				    bottom="8mm">
		  <fo:block font-family="sans"
			    font-weight="bold"
			    margin-left="2mm"
			    margin-right="2mm"
			    font-size="22pt"
			    text-align="center">
		    <xsl:value-of
			select=".//abcd:InformalNameString" />
		  </fo:block>
		</fo:block-container>

		<!-- ** Plant ID ** -->
		<!-- border="solid purple 1px" -->
		<fo:block-container absolute-position="absolute"
				    top="52mm"
				    bottom="0mm"
				    left="2mm"
				    right="66mm">
		  <fo:block font-family="serif"
			    font-size="15pt"
			    text-align="left">
		    <xsl:value-of select="abcd:UnitID" />
		  </fo:block>
		</fo:block-container>

		<!-- ** Distribution ** -->
		<!-- border="solid orange 1px" -->
		<fo:block-container absolute-position="absolute"
				    top="52mm"
				    bottom="0mm"
				    right="2mm"
				    left="55mm"				    
				    display-align="after">
		  <fo:block font-family="serif"
			    font-size="15pt"
			    text-align="right">
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
