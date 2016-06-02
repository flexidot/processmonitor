import psutil
import time
import sendgrid
import subprocess
import configparser
import util
from models import ProcessTimeSeries, getSession

start_time = time.time()

# initial setup
config = util.readConfig()
logger = util.getLogger(config)
sg = util.getSendGrid(config)
session = getSession(config)

# go through all the processes and see if they need logging or restarting
count = 0

# iterate of all processes, log them and restart them if necessary
for p in psutil.process_iter():
    count += 1
    util.logProcess(p, config)
logger.info('found a total of %d processes' % count)

# see if any processes need to be started
util.startProcessesNotFound(config)
logger.debug("The process took %f seconds to run" % (time.time() - start_time))
exit(0)
