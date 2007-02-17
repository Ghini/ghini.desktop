<fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<fo:layout-master-set>
		<!-- layout for the first page -->
		<fo:simple-page-master master-name="first" page-height="29.7cm"
			page-width="21cm" margin-top="10cm" margin-bottom="10cm"
			margin-left="10cm" margin-right="10cm">
			<fo:region-before extent="18cm" />
			<fo:region-body margin-top="18cm" />
			<fo:region-after extent="6.5cm" />
		</fo:simple-page-master>
		<!-- layout for the other pages -->
		<fo:simple-page-master master-name="rest" height="29.7cm"
			width="21cm" margin-top="1cm" margin-bottom="2cm" margin-left="2.5cm"
			margin-right="2.5cm">
			<fo:region-before extent="2.5cm" />
			<fo:region-body margin-top="2.5cm" margin-bottom="5.0cm" />
			<fo:region-after extent="1.5cm" />
		</fo:simple-page-master>

		<!-- How should the sequence of pages appear? -->
		<fo:page-sequence-master master-name="PageLayout">
			<fo:repeatable-page-master-reference master-name="rest" />
		</fo:page-sequence-master>

	</fo:layout-master-set>
	<!-- end: defines page layout -->

	<!-- actual layout -->

	<!-- Title Page -->
	<fo:page-sequence master-name="first">
		<!-- header -->
		<fo:static-content flow-name="xsl-region-before">
			<!-- Inserts a leader (rule). 
				Because leader is an inline fo you have to
				wrap it into a block element  -->
			<fo:block text-align="end" font-size="10pt"
				font-family="serif" line-height="14pt">
				Version
				<xsl:value-of select=".//verson" />
				,
				<xsl:value-of select=".//doctitle" />
			</fo:block>
		</fo:static-content>
	</fo:page-sequence>

	<!-- Make a separate sequence for the non cover sheet -->
	<fo:page-sequence master-name="PageLayout">
		<!-- header -->
		<fo:static-content flow-name="xsl-region-before">
			<!-- Inserts a leader (rule). 
				Because leader is an inline fo you have to
				wrap it into a block element  -->
			<fo:block text-align="end" font-size="10pt"
				font-family="serif" line-height="14pt">
				Version
				<xsl:value-of select=".//verson" />
				,
				<xsl:value-of select=".//doctitle" />
				<fo:leader leader-pattern="rule"
					space-before.optimum="2pt" space-after.optimum="6pt"
					start-indent="0cm" end-indent="0cm" />
			</fo:block>
		</fo:static-content>

		<!-- footer -->
		<fo:static-content flow-name="xsl-region-after">
			<fo:block text-align="end" font-size="10pt"
				font-family="serif" line-height="14pt">
				Page
				<fo:page-number />
			</fo:block>
		</fo:static-content>

		<!-- Main Body-->
		<fo:flow flow-name="xsl-region-body">
			<xsl:apply-templates />
		</fo:flow>
	</fo:page-sequence>
</fo:root>