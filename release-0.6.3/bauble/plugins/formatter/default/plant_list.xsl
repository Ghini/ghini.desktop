<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:fo="http://www.w3.org/1999/XSL/Format"
	xmlns:abcd="http://www.tdwg.org/schemas/abcd/2.06" version="1.0">


	<xsl:template match="abcd:DataSets">
		<fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
			<fo:layout-master-set>
				<fo:simple-page-master master-name="letter"
					page-height="8.5in" page-width="11in" margin-top="0.5in"
					margin-bottom="0.5in" margin-left="0.5in" margin-right="0.5in">
					<fo:region-body/>
				</fo:simple-page-master>
			</fo:layout-master-set>

			<fo:page-sequence master-reference="letter">
				<fo:flow flow-name="xsl-region-body">
					<xsl:for-each select="abcd:DataSet">
						<fo:table table-layout="fixed" inline-progression-dimension="100%">
							<fo:table-column column-width="proportional-column-width(1)"/>
							<fo:table-column column-width="proportional-column-width(3)"/>
							<fo:table-header border="1pt solor #B7B7B7" background-color="#B7B7B7">
								<fo:table-row>
									<fo:table-cell>
									<fo:block>
										ID
										</fo:block>
									</fo:table-cell>
									<fo:table-cell>
									<fo:block>
										Name
										</fo:block>
									</fo:table-cell>
								</fo:table-row>
							</fo:table-header>
							<fo:table-body>
								<xsl:for-each select=".//abcd:Unit">
									<fo:table-row>
										<fo:table-cell border="1pt solid black" padding=".25em">
											<fo:block>
												<xsl:value-of
													select="abcd:UnitID" />
											</fo:block>
										</fo:table-cell>
										<fo:table-cell border="1pt solid black" padding=".25em">
											<fo:block>
												<xsl:value-of
													select=".//abcd:FullScientificNameString" />
											</fo:block>
										</fo:table-cell>
									</fo:table-row>
								</xsl:for-each>
							</fo:table-body>
						</fo:table>
					</xsl:for-each>
				</fo:flow>
			</fo:page-sequence>
		</fo:root>
	</xsl:template>

</xsl:stylesheet>