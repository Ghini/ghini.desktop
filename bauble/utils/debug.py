#
# an output debugger
#

# TODO: i don't think this works right now

class _debug(object):
    
    def __call_holder__(self, msg):
        print msg

    __call__ = lambda x, y: True


    def _set_enable(self, enable):
        if enable:
            self.__class__.__call__ = self.__call_holder__
        else:
            self.__class__.__call__ = lambda x, y: True

    enable = property(None, _set_enable) # no getter
    

debug = _debug()
