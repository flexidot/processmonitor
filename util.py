import json
import psutil
import time, datetime
import sendgrid
import logging, subprocess
from models import ProcessTimeSeries, ProcessRestart

VERSION = 0.11
# some defaults
PROCESS_RUNNING = 0
PROCESS_NOT_RUNNING = 1
MAX_RESTART_TRIES = 3

# reasons for restarts
RESTART_REASON_TOO_MUCH_MEM = 1
RESTART_REASON_PROCESS_NOT_FOUND = 2

# reads a default config file of config.json in  the same directory
# retrns a dict of all the values.
def readConfig():
    json1_file = open('config.json')
    json1_str = json1_file.read()
    json1_data = json.loads(json1_str)
    #print (json1_data['SendGridInfo']['APIKey'])
    #print ('number of processes to be monitored are %d' % len(json1_data['ProcessNames']))
    return json1_data

def getLogger(config):
    # setup logging
    logger = logging.getLogger(config['ProcessName'])
    logger.setLevel(config['DefaultLogLevel'])
    fh = logging.FileHandler(config['LogFileName'])
    fh.setLevel(config['DefaultLogLevel'])
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    ch.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    config['logger'] = logger
    return logger

def getSendGrid(config):
	logger = config['logger']
	sg = None
	if (config['SMTPAlert']) == 'Yes':
		logger.info('SMTPAlert is enabled')
		sg = sendgrid.SendGridClient(config['SendGridInfo']['APIKey'])
		config['sg'] = sg
	else:
		logger.info('SMTPAlert is NOT enabled')
	return sg

# given a command to restart a process, it runs taht command
def restart_process(name, cmd, config, reason):
    session = config['session']
    logger = config['logger']
    stdoutdata = subprocess.getoutput(cmd)
    logger.debug(stdoutdata)

    restartlog = ProcessRestart(time = time.time(), name = name,
        reason = reason)
    session.add(restartlog)

# check if a process needs to be restarted
def checkProcess(process, processconfig, config):
    logger = config['logger']

    logger.debug("Entering checkProcess for %s with config for %s" % (process.name, processconfig['ProcessName']))
    assert process.name == processconfig['ProcessName']

    # let's find out the criteria to restart this process
    maxcpuusage = int(processconfig['CPURestartLevel'])
    maxmemusage = int(processconfig['MemoryRestartLevel'])
    memused = process.get_memory_info()[0]
    totalmem = psutil.virtual_memory()[0]
    mempercent = memused*100 / totalmem
    logger.info("Process %s using %f memory which is %f percent" % (process.name, memused, mempercent))

    if mempercent > maxmemusage:
        logger.error("Process %s using too much memory. restarting it." % process.name)
        restart_process(process.name, processconfig['RestartCommand'], RESTART_REASON_TOO_MUCH_MEM, config)
    return

def logTimeSeries(p, config):
    logger = config['logger']
    session = config['session']
    t = ProcessTimeSeries(time = p.create_time, pid = p.pid,
        name = p.name, memusage = p.get_memory_info()[0], cpuusage = 0)
    session.add(t)

def logProcess(p, config):
    logger = config['logger']
    session = config['session']
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time))
    mem = p.get_memory_info()[0] / float(2 ** 20)
    logger.info('name %s, pid %d, start time %s, mem %d percent, cpu' % (p.name, p.pid, start_time, mem))

    # log this process, if we are required to log all processes or
    # required to log this particular process
    if config['AllProcessLogging'] == 'Yes':
        logTimeSeries(p, config)

    for piter in config['ProcessNames']:
        if piter['ProcessName'] == p.name:
            # now that we have found this process, let's remember that
            # that way, we can easily find processes that need to be restarted
            piter['FoundProcess'] = 'Yes'
            logger.debug("Found config for process %s " % p.name)

            # check if we need to restart this process
            checkProcess(p, piter, config)

            # log this process if we are required to and if we have not already
            # logged all processes
            if config['AllProcessLogging'] == 'No' and  piter['ProcessLogging'] == 'Yes':
                logTimeSeries(p, config)
            break
    return

def startProcessesNotFound(config):
    logger = config['logger']
    # go through and find out which processes need to be running but are not running
    for piter in config['ProcessNames']:
        try:
            if piter['FoundProcess'] == 'Yes':
                logger.info("Found process %s" % piter['ProcessName'])
        except KeyError:
            logger.error("%s is NOT running. Attempt to start with %s" % (piter['ProcessName'], piter['RestartCommand']))
            process_alert(piter['ProcessName'], config)
            restart_process(piter['ProcessName'], piter['RestartCommand'], config, RESTART_REASON_PROCESS_NOT_FOUND)

# send a message if a process is not running.
def process_alert(name, config):
	sg = config['sg']
	logger = config['logger']
	message = sendgrid.Mail()
	smtp_to = config['SendGridInfo']['SmtpTo']
	smtp_cc = config['SendGridInfo']['SmtpCC']
	smtp_from = config['SendGridInfo']['SmtpFrom']
	message.add_to(smtp_to)
	message.add_to(smtp_cc)
	message.set_subject("ALERT: critical process NOT running")
	message.set_html("%s is NOT running. attempting to restart it." % name)
	message.set_text("%s is NOT running. attempting to restart it." % name)
	message.set_from(smtp_from)
	status, msg = sg.send(message)
	logger.debug("sent alert message to %s with status %s and msg %s" % (smtp_to, status, msg))

def printhelp():
    print ("This is how to use the program")

def printversion():
    print ("version: %s" % VERSION)

def printrestarts(config):
    session = config['session']
    logger = config['logger']
    for r in session.query(ProcessRestart).all():
        #t = datetime.datetime(r.time)
        #t = r.time
        #t = time.time(r.time)
        print ("Restarted process %s and reason %d at %s" % (r.name, r.reason,
            #datetime.datetime.fromtimestamp(r.time).strftime("%Y-%m-%d %H:%M:%S")))
            datetime.datetime.fromtimestamp(r.time).strftime("%a, %d %b %Y %H:%M:%S -0800")))
            #strftime("%a, %d %b %Y %H:%M:%S +0000",t)))
