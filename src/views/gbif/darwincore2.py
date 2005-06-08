#
# darwincore2.py
#
# Description: create darwin core response and request markup

import string

# TODO: could make a generic template in digir.py and if you choose the
# darwin core schema then only replace those elements specific to darwincore
# in the generic template

test = """
<?xml version="1.0" encoding="UTF-8"?>
xmlns='http://digir.net/schema/protocol/2003/1.0'
xmlns:xsd='http://www.w3.org/2001/XMLSchema'
xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
xmlns:digir='http://digir.net/schema/protocol/2003/1.0'
xmlns:dwc='http://digir.net/schema/conceptual/darwin/2003/1.0'
xmlns:darwin='http://digir.net/schema/conceptual/darwin/2003/1.0'
xsi:schemaLocation='http://digir.net/schema/protocol/2003/1.0'
http://digir.sourceforge.net/schema/protocol/2003/1.0/digir.xsd'
"""

#<?xml version="1.0" encoding="UTF-8"?>
inventory_request_template = string.Template("""<request xmlns="http://www.namespaceTBD.org/digir" 
         xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
         xmlns:darwin="http://digir.net/schema/conceptual/darwin/2003/1.0">
  <header>
    <version>1.0.0</version>
    <sendTime>$sendtime</sendTime>
    <source>127.0.0.1</source>
    <destination resource="$resource">$destination</destination>
    <type>inventory</type>
  </header>
  <inventory>
    <filter>
        $filter
    </filter>
    <darwin:ScientificName />
    <count>true</count>
  </inventory>
</request>
""")

# 
# need to replace $sendtime, $destination, $filter
#<?xml version="1.0" encoding="UTF-8"?>
search_request_template = string.Template("""<request 
    xmlns="http://digir.net/schema/protocol/2003/1.0" 
    xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
    xmlns:darwin="http://digir.net/schema/conceptual/darwin/2003/1.0" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
    xsi:schemaLocation="http://digir.net/schema/protocol/2003/1.0 
      http://digir.sourceforge.net/schema/protocol/2003/1.0/digir.xsd 
      http://digir.net/schema/conceptual/darwin/2003/1.0 
      http://digir.sourceforge.net/schema/conceptual/darwin/2003/1.0/darwin2.xsd">
    <header>
      <version>1.0</version>
      <sendTime>$sendtime</sendTime>
      <source>127.0.0.1</source>
      <destination resource="$resource">$destination</destination>
      <type>search</type>
    </header>
    <search>
      <filter>
          $filter
      </filter>
      <records limit="3" start="0">
        <structure>
          <xsd:element name="record">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element ref="darwin:InstitutionCode"/>
                <xsd:element ref="darwin:CollectionCode"/>
                <xsd:element ref="darwin:CatalogNumber"/>
                <xsd:element ref="darwin:ScientificName"/>
                <xsd:element name="coordinates">
                  <xsd:complexType>
                     <xsd:sequence>
                      <xsd:element ref="darwin:Latitude"/>
                      <xsd:element ref="darwin:Longitude"/>
                     </xsd:sequence>
                  </xsd:complexType>
                </xsd:element>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </structure>
      </records>
      <count>true</count>
    </search>
 </request>
""")


"""
<request 
  xmlns="http://digir.net/schema/protocol/2003/1.0" 
  xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
  xmlns:darwin="http://digir.net/schema/conceptual/darwin/2003/1.0" 
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
  xsi:schemaLocation="http://digir.net/schema/protocol/2003/1.0 
    http://digir.sourceforge.net/schema/protocol/2003/1.0/digir.xsd 
    http://digir.net/schema/conceptual/darwin/2003/1.0 
    http://digir.sourceforge.net/schema/conceptual/darwin/2003/1.0/darwin2.xsd">
<header>
  <version>1.0</version>
  <sendTime>2003-03-09T19:14:58-05:00</sendTime>
  <source>216.91.87.102</source>
  <destination resource="test">http://localhost/DiGIR/DiGIR.php</destination>
  <type>search</type>
</header>
<search>
  <filter>
  <like>
    <darwin:ScientificName>f%</darwin:ScientificName>
  </like>
  </filter>
    <records limit="10" start="0">
    <structure schemaLocation="http://digir.sourceforge.net/schema/conceptual/darwin/brief/2003/1.0/darwin2brief.xsd"/>
    </records>
  <count>true</count>
</search>
</request>
"""

