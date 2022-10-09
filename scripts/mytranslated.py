#!/usr/bin/env python
# -*- coding: utf-8 -*-
from optparse import OptionParser
import imp
usage = 'usage: %prog [options]'
parser = OptionParser(usage)
parser.add_option('-f', '--from', dest='translation_from', default='en',
                  help='the language to translate from')
parser.add_option('-t', '--to', dest='translation_to', default='es',
                  help='the language to translate to')

options, args = parser.parse_args()

translation_from = options.translation_from
translation_to = options.translation_to

import sys  
imp.reload(sys)  
sys.setdefaultencoding('utf8')

import codecs
import json
import requests

def translate(s):
    try:
        r = requests.get('http://api.mymemory.translated.net/get?q=%s&langpair=%s|%s' % (s, translation_from, translation_to), timeout=6)
    except requests.exceptions.ReadTimeout as e:
        print(type(e), e, file=sys.stderr)
        return ""
        
    j = json.loads(r.text)
    reply = j['responseData']['translatedText']
    if reply is None:
        print(r.text, file=sys.stderr)
        return ""

    for k in ['INVALID LANGUAGE PAIR SPECIFIED.', 'NO QUERY SPECIFIED', 'QUERY LENGTH LIMIT EXCEDEED', 'MYMEMORY WARNING:']:
        if reply.startswith(k):
            print(reply, file=sys.stderr)
            return ""
    return reply

about_to_stop = False

import fileinput, re
for line in fileinput.input(args):
    text = str(line.strip())
    if not text:
        if about_to_stop == True:
            break
        about_to_stop = True
        continue  # skip any empty lines
    print(translate(line))
