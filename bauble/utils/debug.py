#
# an output debugger
#


import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# this should go in utils or somethiing
class _debug(object):
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(filename)s(%(lineno)d): %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger('debugger')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    _enabled = True
    
    __call__ = lambda x, y: True
        
    @classmethod
    def __call_holder__(cls, msg):    
        return cls.logger.debug(msg)
        
    def _get_enabled(self):
        return self._enabled
        
    def _set_enabled(self, enable):
        self._enabled = enable
        if enable:
            self.__class__.__call__ = self.__class__.__call_holder__
        else: 
            self.__class__.__call__ = lambda x, y: True
        
    enabled = property(fget=_get_enabled, fset=_set_enabled)
    
debug = _debug()    
debug.enabled = True

# alias for other logging
log = logging


#
#
#class _debug_old(object):
#    
#    def __call_holder__(self, msg):
#        sys.stderr.write("%s\n" % msg)
#
#    __call__ = lambda x, y: True
#
#
#    def _set_enable(self, enable):
#        if enable:
#            self.__class__.__call__ = self.__call_holder__
#        else:
#            self.__class__.__call__ = lambda x, y: True
#
#    enable = property(None, _set_enable) # no getter
    

#debug = _debug()
