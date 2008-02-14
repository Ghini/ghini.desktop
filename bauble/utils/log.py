#
# logger/debugger for Bauble
#
import os, sys, logging
import bauble.utils
from bauble.i18n import *

def _main_is_frozen():
    import imp
    return (hasattr(sys, "frozen") or # new py2exe
	    hasattr(sys, "importers") or # old py2exe
	    imp.is_frozen("__main__")) # tools/freeze


def _default_handler():
    import bauble.paths as paths
    if _main_is_frozen():
        # TODO: should make sure we can open this file and it's writeable
        filename = os.path.join(paths.user_dir(), 'bauble.log')
        handler = logging.FileHandler(filename, 'w+')
        sys.stdout = open(filename, 'w+')
        sys.stderr = open(filename, 'w+')
    else:
        handler = logging.StreamHandler()
    return handler


# warning: HACK! so the error message only shows once
__yesyesiknow = False

def _config_logger(name, level, format, propagate=False):
    try:
        handler = _default_handler()
    except IOError, e:
        import traceback

        # TODO: popup a dialog telling the user that the default logger
        # couldn't be started??
        global __yesyesiknow
        if not __yesyesiknow and not _main_is_frozen():
            msg = _('** Could not open the default log file.\n'\
                    'Press any key to continue.\n\n%s') % \
                    bauble.utils.xml_safe_utf8(e)
            utils.message_details_dialog(msg, traceback.format_exc())
            __yesyesiknow = True
        handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.propagate = propagate
    return logger


def sa_echo(logger='sqlalchemy', level=logging.DEBUG):
    bauble.engine.echo = True
    logging.getLogger(logger).setLevel(level)


def echo(toggle=True):
    if toggle == True:
        bauble.engine.echo = False
        sa_echo(level=logging.DEBUG)
    else:
        bauble.engine.echo = True
        sa_echo(level=logging.ERROR)



logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
#root_logger = _config_logger('', logging.DEBUG, '%(levelname)s: %(message)s',
#			     True)

# info logger, prints only the message
info_logger = _config_logger('bauble.info',logging.INFO, '%(message)s')
info = info_logger.info

# debug logger, prints file and line name with the message
debug_logger = _config_logger('bauble.debug', logging.DEBUG,
			     '%(filename)s(%(lineno)d): %(message)s')
debug = debug_logger.debug

# warning logger
warning_logger = _config_logger('bauble.warning', logging.WARNING,
			     '%(filename)s(%(lineno)d): %(message)s')
warning = warning_logger.warning


# error logger
error_logger = _config_logger('bauble.error', logging.ERROR,
			     '%(filename)s(%(lineno)d): %(message)s')
error = error_logger.error


class log:

    @staticmethod
    def debug(*args, **kw):
        debug(*args, **kw)

    @staticmethod
    def info(*args, **kw):
        info(*args, **kw)

    @staticmethod
    def warning(*args, **kw):
        logging.warning(*args, **kw)

    @staticmethod
    def error(*args, **kw):
        logging.error(*args, **kw)

warning = log.warning
error = log.error

# TODO: main won't work if it can't find bauble, the only reason we have
# to import bauble is for main_is_frozen in _default_handler() if we could
# work around this then we could run this file directly to test it, we could
# either include our own main_is_frozen() here or do a try..except block
# around _default_handler(), both are pretty ugly
# TODO: turn this into a test of the logger, in the test we should delete
# the log file and make sure that we if we write to a log when there is no log
# file then it doesn't crash
if __name__ == "__main__":
    log.debug('log.debug message')
    debug('debug message')
    log.info('log.info message')
    info('info message')
    log.warning('log.warning message')
    warning('warning message')
    log.error('log.error message')
    error('error message')
