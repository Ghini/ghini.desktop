#!/usr/bin/env python

import httplib
httplib.HTTPConnection.debuglevel = 1
import urllib2
import urllib
import darwincore2
from datetime import datetime
import sys
        
        
def urllib_get_response(url, data=None):
    import urllib2
    req = urllib2.Request(url)#, data)
    f = urllib2.urlopen(req)
    result = f.read()
    if hasattr(f, "headers"):
        print f.headers
    return result
    
filter = filter = """<equals>
            <darwin:Genus>
            Maxillaria
            </darwin:Genus>
            </equals>"""
base_url = "digir.mobot.org:80"
sub_url = "/digir/DiGIR.php"
url = "http://" + base_url + sub_url
#url = "http://digir.mobot.org:80"
url = "http://digir.mobot.org:80/digir/DiGIR.php"
data = darwincore2.inventory_request_template.substitute(filter=filter, 
                                                     sendtime=datetime.utcnow(),
                                                     destination=url,
                                                     resource="MOBOT")
print data
import xml.parsers.expat
import xml.dom.minidom


#http://localhost/provtest/DiGIR.php?request=http://localhost/req1.xml                                                     

#data = data.replace("\n", "")                                                     
dom = xml.dom.minidom.parseString(unicode(data, "utf-8"))
data = urllib.quote(dom.toxml())
url = url+"?doc="+data
print url
#headers = {"Content-type": "text/xml",
#            "Accept": "text/plain"}
#conn = httplib.HTTPConnection(base_url)

#conn.request("POST", sub_url, data, headers)
#response = conn.getresponse()
#print response.read()

req = urllib2.Request(url, data)
f = urllib2.urlopen(req)
result = f.read()
print result
sys.stderr.flush()