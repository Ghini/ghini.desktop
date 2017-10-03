#!/usr/bin/env python
# -*- coding: utf-8 -*-

translation_to = 'fr'

import sys  
reload(sys)  
sys.setdefaultencoding('utf8')

import codecs
import json
import requests

def translate(s):
    try:
        r = requests.get('http://api.mymemory.translated.net/get?q=%s&langpair=en|%s' % (s, translation_to), timeout=6)
    except requests.exceptions.ReadTimeout, e:
        print >> sys.stderr, type(e), e
        return ""
        
    j = json.loads(r.text)
    reply = j['responseData']['translatedText']
    if reply is None:
        print >> sys.stderr, r.text
        return ""

    for k in ['INVALID LANGUAGE PAIR SPECIFIED.', 'NO QUERY SPECIFIED', 'QUERY LENGTH LIMIT EXCEDEED', 'MYMEMORY WARNING:']:
        if reply.startswith(k):
            print >> sys.stderr, reply
            return ""
    return reply

about_to_stop = False

import fileinput, re
for line in fileinput.input():
    text = unicode(line.strip())
    if not text:
        if about_to_stop == True:
            break
        about_to_stop = True
        continue  # skip any empty lines
    print translate(line)
