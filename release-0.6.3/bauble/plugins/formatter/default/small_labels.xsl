<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:fo="http://www.w3.org/1999/XSL/Format"
	xmlns:abcd="http://www.tdwg.org/schemas/abcd/2.06" version="1.0">

	<xsl:template match="abcd:DataSets">

		<fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
			<fo:layout-master-set>
				<fo:simple-page-master master-name="letter"
					page-height="11in" page-width="8.5in" margin-top="0.5in"
					margin-bottom="0.5in" margin-left="0.5in" margin-right="0.5in">
					<fo:region-body column-count="2" column-gap='1mm' />
				</fo:simple-page-master>
			</fo:layout-master-set>

			<fo:page-sequence master-reference="letter">
				<fo:flow flow-name="xsl-region-body">
					<xsl:for-each select="abcd:DataSet">
						<xsl:for-each select=".//abcd:Unit">

							<!-- ** the label block ** -->
							<fo:block-container margin='1mm'
								keep-together='always' border="solid black 1px" width='78mm'
								height='45mm'>

								<!-- ** Family ** -->
								<fo:block-container
									absolute-position="absolute" top="5mm" bottom="32mm">
									<fo:block font-weight="bold"
										margin-left="5mm" margin-right="5mm" font-size="14pt"
										text-align="center">
										<xsl:value-of
											select='.//abcd:HigherTaxonName' />
									</fo:block>
								</fo:block-container>

								<!-- ** Scientific Name ** -->
								<fo:block-container
									absolute-position="absolute" top="14mm" bottom="22mm">
									<fo:block font-style='italic'
										margin-left="5mm" margin-right="5mm" font-size="12pt"
										text-align="center">
										<xsl:value-of
											select='.//abcd:FullScientificNameString' />
										<!--
											<fo:inline margin-right='2mm' >
											<xsl:value-of select=".//genusormonomial"/>
											</fo:inline>
											<fo:inline>
											<xsl:value-of select=".//firstepithet"/>
											</fo:inline>
										-->
									</fo:block>
								</fo:block-container>

								<!-- ** Vernacular name ** -->
								<fo:block-container
									absolute-position="absolute" top="23mm" bottom="12mm">
									<fo:block font-weight="bold"
										margin-left="5mm" margin-right="5mm" font-size="16pt"
										text-align="center">
										<xsl:value-of
											select=".//abcd:InformalNameString" />
									</fo:block>
								</fo:block-container>

								<!-- ** Plant ID ** -->
								<fo:block-container
									absolute-position="absolute" top='39mm' bottom="0mm" left="2mm"
									width="37mm">
									<fo:block font-size="12pt"
										text-align="left">
										<xsl:value-of
											select="abcd:UnitID" />
									</fo:block>
								</fo:block-container>

								<!-- ** Distribution ** -->
								<!--<fo:block-container absolute-position="absolute" top='40mm' bottom="0mm" right="2mm" width="37mm" border="solid orange 1px">-->
								<fo:block-container
									absolute-position="absolute" top='39mm' bottom="0mm"
									right="2mm" width="37mm">
									<fo:block font-size="12pt"
										text-align="right">
										<xsl:value-of
											select="distribution" />
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

