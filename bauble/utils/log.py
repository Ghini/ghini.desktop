#
# an output debugger
#


import sys, logging
import logging

# alias for logging, just b/c its three less letters
log = logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

# debugging convenience
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(filename)s(%(lineno)d): %(message)s')
handler.setFormatter(formatter)
_debug = logging.getLogger('debugger')
_debug.propagate = False
_debug.addHandler(handler)
_debug.setLevel(logging.DEBUG)
debug = _debug.debug
