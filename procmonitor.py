import psutil
import time
import sendgrid
import subprocess
import configparser
import util
from models import ProcessTimeSeries, getSession

# initial setup
config = util.readConfig()
logger = util.getLogger(config)
sg = util.getSendGrid(config)
session = getSession(config)

# go through all the processes and see if they need logging or restarting
util.iterateAllProcesses(config)

# see if any processes need to be started
util.startProcessesNotFound(config)
exit(0)
