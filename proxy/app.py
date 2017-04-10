import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from common import constants
import atexit
import signal
import time
from flask import Config

# Find paths
instance_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'instance'
resource_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'resource'

# Create logger
file_handler = RotatingFileHandler(os.path.join(instance_path, 'garage_proxy.log'),
                                   constants.LOGFILE_MODE, constants.LOGFILE_MAXSIZE,
                                   constants.LOGFILE_BACKUP_COUNT)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(constants.LOGFILE_FORMAT))
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]"))
logger = logging.Logger("PROXY", level=logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# Log startup
logger.info('---------- Proxy starting up!')

try:
    # Load configuration
    logger.info('Loading configuration')
    config_file = os.path.join(instance_path, 'app.cfg')
    default_config_file = os.path.join(resource_path, 'default_app.cfg')
    config = Config(instance_path)
    config.from_pyfile(default_config_file)
    config.from_pyfile(config_file)

except:
    logger.exception('Exception during startup actions')
    raise

finalized = False
simple = True
proxy = None

# Set up application finalizer
def finalize():
    global finalized
    global proxy
    proxy.stop_monitor()
    logger.info('Entering finalizer.')
    if finalized:
        logger.info('Finalizer already called. Skipping...')
        return
    finalized = True
    return

logger.info('Registering finalizer')
atexit.register(finalize)

# Set up so SIGTERM will cause graceful shutdown
def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    logger.info('SIGTERM received!')
    finalize()
    logger.info('Proxy terminated correctly')
    sys.exit(0)

logger.info('Registering SIGTERM handler')
signal.signal(signal.SIGTERM, sigterm_handler)

logger.info('Finished with startup actions')

# Provide startup routine
def main():
    global proxy
    logger.info('Starting proxy')
    try:
        from proxy.proxy import GaragePiProxy
        proxy = GaragePiProxy()
        proxy.start()
        while True:
            global simple
            if simple:
                proxy.start_monitor()
            else:
                monitor = True
                if monitor:
                    timeout = proxy.monitor()
                    if timeout:
                        time.sleep(500)
                else:
                    time.sleep(1000)

    except Exception as e:
        logger.exception(e)
        logger.exception('Exception while running proxy')
    finally:
        logger.debug('Entered finally')
        finalize()
        logger.info('Exiting')