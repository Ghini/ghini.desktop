<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    version="1.0">
    <xsl:template match='units'>
        <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
        <fo:layout-master-set>
            <fo:simple-page-master master-name="main-page">
                <fo:region-body margin=".5in"/>
            </fo:simple-page-master>
        </fo:layout-master-set>    
        
        <fo:page-sequence master-reference="main-page">
        <fo:flow flow-name="xsl-region-body">
        <xsl:for-each select="unit">
            <fo:float float="left">            
                <fo:block margin='1mm'>
	                <fo:block-container border="solid black 1px" width='78mm' height='45mm'>
	                    <!--<fo:block-container absolute-position="absolute" top="5mm" bottom="32mm" border="solid blue 1px">-->
	                    <fo:block-container absolute-position="absolute" top="5mm" bottom="32mm">
	                        <fo:block font-weight="bold" margin-left="5mm" margin-right="5mm"  font-size="14pt" text-align="center">
	                            <xsl:value-of select='.//highertaxonname'/>
	                        </fo:block>
	                    </fo:block-container>
	                    <!--<fo:block-container absolute-position="absolute" top="14mm" bottom="26mm" border="solid red 1px">-->
	                    <fo:block-container absolute-position="absolute" top="14mm" bottom="26mm">
	                        <fo:block font-style='italic' margin-left="5mm" margin-right="5mm" font-size="15pt" text-align="center">
	                            <fo:inline margin-right='2mm' ><xsl:value-of select=".//genusormonomial"/></fo:inline>                                               
	                            <fo:inline><xsl:value-of select=".//firstepithet"/></fo:inline>
	                        </fo:block>
	                    </fo:block-container>
	                    <!--<fo:block-container absolute-position="absolute" top="23mm" bottom="12mm" border="solid green 1px">-->
	                    <fo:block-container absolute-position="absolute" top="23mm" bottom="12mm">                    
	                        <fo:block font-weight="bold" margin-left="5mm" margin-right="5mm" font-size="16pt" text-align="center">
	                            <xsl:value-of select=".//informalnamestring"/>
	                        </fo:block>
	                    </fo:block-container>
	                    <!--<fo:block-container absolute-position="absolute" top='40mm' bottom="0mm" left="2mm" width="37mm" border="solid yellow 1px">-->
	                    <fo:block-container absolute-position="absolute" top='39mm' bottom="0mm" left="2mm" width="37mm">                    
	                        <fo:block font-size="12pt" text-align="left"><xsl:value-of select="unitid"/></fo:block>                
	                    </fo:block-container>
	                    <!--<fo:block-container absolute-position="absolute" top='40mm' bottom="0mm" right="2mm" width="37mm" border="solid orange 1px">-->
	                    <fo:block-container absolute-position="absolute" top='39mm' bottom="0mm" right="2mm" width="37mm">
	                        <fo:block font-size="12pt" text-align="right"><xsl:value-of select=".//origin"/></fo:block>
	                    </fo:block-container>
	                </fo:block-container>
                </fo:block>
             </fo:float>            
        </xsl:for-each>
        </fo:flow>
        </fo:page-sequence>
        </fo:root>
    </xsl:template>
</xsl:stylesheet>

