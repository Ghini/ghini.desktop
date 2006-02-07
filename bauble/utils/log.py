#
# logger/debugger for Bauble
#
import os, sys, logging
import bauble

if bauble.main_is_frozen():
    import bauble.paths as paths    
    filename = os.path.join(paths.user_dir(), 'bauble.log')
    debug_handler = logging.FileHandler(filename)    
    logging_config = {'level': logging.DEBUG, 
                      'format': '%(message)s',
                      'filename': filename}
else:
    debug_handler = logging.StreamHandler()
    logging_config = {'level': logging.DEBUG, 
                      'format': '%(message)s',
                      'stream': sys.stderr}
                     
logging.basicConfig(**logging_config)

# add the custom handler for the debug logger
debug_handler.setLevel(logging.DEBUG)
debug_formatter = logging.Formatter('%(filename)s(%(lineno)d): %(message)s')
debug_handler.setFormatter(debug_formatter)
logging.getLogger('').addHandler(debug_handler)

# alias for debug
debug = logging.debug

# alias for logging, just b/c its three less letters
log = logging
