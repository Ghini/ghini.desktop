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
				    top="7mm" bottom="32mm">
		  <fo:block font-family="Bitstream Vera Sans, sans" 
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
		<fo:block-container absolute-position="absolute" 
				    top="17mm" 
				    bottom="12mm">
		  <fo:block line-height=".9"
			    font-size="23pt" 
			    font-family="Bitstream Vera Serif, serif"
			    font-style="italic" 
			    font-weight="500" 
			    margin-left="2mm"
			    margin-right="2mm" 
			    text-align="center">
		    <xsl:value-of select=".//abcd:FullScientificNameString" />
		    <!--
			<fo:inline space-end="6pt">
			<xsl:value-of select=".//genusormonomial"/>
			</fo:inline>
			<fo:inline>
			<xsl:value-of select=".//firstepithet"/>
			</fo:inline>
		    -->
		  </fo:block>
		</fo:block-container>
		
		<!-- ** Vernacular name ** -->
		<fo:block-container absolute-position="absolute" 
				    top="33mm" 
				    bottom="12mm">
		  <fo:block font-family="Bitstream Vera Sans, sans" 
			    font-weight="bold"
			    margin-left="5mm" 
			    margin-right="5mm" 
			    font-size="22pt"
			    text-align="center">
		    <xsl:value-of
			select=".//abcd:InformalNameString" />
		  </fo:block>
		</fo:block-container>
		
		<!-- ** Plant ID ** -->
		<fo:block-container absolute-position="absolute" 
				    top="52mm" 
				    bottom="0mm" 
				    left="2mm"
				    width="50mm">
		  <fo:block font-family="Bitstream Vera Serif, serif" 
			    font-size="15pt"
			    text-align="left">
		    <xsl:value-of select="abcd:UnitID" />
		  </fo:block>
		</fo:block-container>
		
		<!-- ** Distribution ** -->
		<!-- border="solid orange 1px" -->
		<fo:block-container absolute-position="absolute" 
				    top="45mm" 
				    bottom="0mm"
				    left="45mm" 
				    right="2mm" 
				    width="70mm"
				    display-align="after">
		  <fo:block font-family="Bitstream Vera Serif, serif" 
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
