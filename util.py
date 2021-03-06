import json
import psutil
import time, datetime
import sendgrid
import logging, subprocess
from models import Database

VERSION = 0.20
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
    logger = config['logger']
    stdoutdata = subprocess.getoutput(cmd)
    logger.debug(stdoutdata)
    config['db'].addRestartEvent(config, time = time.time(), name = name,
        reason = reason)

def logProcess(p, config):
    logger = config['logger']
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time))
    mem = p.get_memory_info()[0] / float(2 ** 20)
    logger.info('name %s, pid %d, start time %s, mem %d percent, cpu' % (p.name, p.pid, start_time, mem))

    # log this process, if we are required to log all processes or
    # required to log this particular process
    if config['AllProcessLogging'] == 'Yes':
        config['db'].logTimeSeries(p, config)

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
    logger = config['logger']

    for r in config['db'].getRestarts():
        print ("Restarted process %s and reason %d at %s" % (r.name, r.reason,
            datetime.datetime.fromtimestamp(r.time).strftime("%a, %d %b %Y %H:%M:%S -0800")))

def formatmem(m):
    if m < 1024:
        return m
    elif  m < 1024*1024:
        return str(round(m/1024,2)) + "KB"
    elif  m < 1024*1024*1024:
        return str(round(m/(1024*1024),2)) + 'MB'
    else:
        return str(round(m/(1024*1024*1024),2)) + 'GB'

def printtimeseries(config):
    logger = config['logger']

    for processid in config['db'].getProcessIDs():
        print("Process %s, pid %d, started at %s" % (processid.name, processid.pid,
        datetime.datetime.fromtimestamp(processid.timestarted).strftime("%a, %d %b %Y %H:%M:%S -0000")))

        startedmem = 0
        count = 0
        totalmem = 0
        for process in processid.processtimeseries:
            if startedmem == 0:
                startedmem = process.memusage
            count += 1
            totalmem += process.memusage
            mem = formatmem(process.memusage)
            #print("\tmemusage %s at %s" % (mem,
            #    datetime.datetime.fromtimestamp(process.time).strftime("%a, %d %b %Y %H:%M:%S -0000")))

        avgmem = totalmem / count
        #print ("\ttotal %d, count %d, avg %d" % (totalmem, count, avgmem))
        startedmem = formatmem(startedmem)
        avgmem = formatmem(avgmem)
        currentmem = formatmem(process.memusage)

        print("\tcurrent %s, avg %s, initial %s" % (currentmem, startedmem, avgmem))
