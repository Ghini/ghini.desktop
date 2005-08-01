<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    version="1.0">
    <xsl:template match='units'>
        <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
        <fo:layout-master-set>
            <fo:simple-page-master master-name="main-page">
                <fo:region-body margin="1in"/>
            </fo:simple-page-master>
        </fo:layout-master-set>    
        
        <fo:page-sequence master-reference="main-page">
        <fo:flow flow-name="xsl-region-body">
        <xsl:for-each select="unit">            
                <fo:block padding='10mm'>
                <fo:block-container border="solid black 1px" width='80mm' height='45mm'>
                    <fo:block-container absolute-position="absolute" top="5mm" bottom="32mm" border="solid blue 1px">
                        <fo:block margin-left="5mm" margin-right="5mm"  font-size="14pt" text-align="center">
                            <xsl:value-of select='.//highertaxonname'/>
                        </fo:block>
                    </fo:block-container>
                    <fo:block-container absolute-position="absolute" top="14mm" bottom="26mm" border="solid red 1px">                    
                        <fo:block margin-left="5mm" margin-right="5mm" font-size="16pt" text-align="center">
                            <fo:inline><xsl:value-of select=".//genusormonomial"/></fo:inline>                                               
                            <fo:inline><xsl:value-of select=".//firstepithet"/></fo:inline>
                        </fo:block>
                    </fo:block-container>
                    <fo:block-container absolute-position="absolute" top='40mm' bottom="2mm" width="48%" border="solid yellow 1px">                    
                        <fo:block margin-left="5mm" font-size="12pt" text-align="left"><xsl:value-of select="unitid"/></fo:block>                
                    </fo:block-container>
                </fo:block-container>
             </fo:block>
        </xsl:for-each>
        </fo:flow>
        </fo:page-sequence>
        </fo:root>
    </xsl:template>
</xsl:stylesheet>

