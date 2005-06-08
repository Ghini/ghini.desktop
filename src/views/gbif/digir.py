#
# digir.py
#

import string

metadata_request_template = string.Template("""
<?xml version="1.0" encoding="utf-8" ?>
<request xmlns="http://digir.net/schema/protocol/2003/1.0">
  <header>
    <version>1.0.0</version>
    <sendTime>$sendtime</sendTime>
    <source>127.0.0.1</source>
    <destination>$destination</destination>
    <type>metadata</type>
  </header>
</request>
""")

#search_request_template 
#inventory_request_template