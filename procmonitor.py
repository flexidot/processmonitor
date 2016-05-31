import psutil
import time
import sendgrid
import subprocess
import configparser
import util
from models import ProcessTimeSeries, getSession

config = util.readConfig()
logger = util.getLogger(config)
sg = util.getSendGrid(config)
session = getSession(config)

util.iterateAllProcesses(config)
util.startProcessesNotFound(config)
exit(0)
