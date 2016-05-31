import json
import psutil
import time
import sendgrid
import logging
from models import ProcessTimeSeries

# some defaults
PROCESS_RUNNING = 0
PROCESS_NOT_RUNNING = 1
MAX_RESTART_TRIES = 3

# reads a default config file of config.json in  the same directory
# retrns a dict of all the values.
def readConfig():
    print ("in readconfig")
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
    else:
        logger.info('SMTPAlert is NOT enabled')
    return None

# given a command to restart a process, it runs taht command
def restart_process(cmd, config):
    logger = config['logger']
    stdoutdata = subprocess.getoutput(cmd)
    logger.debug(stdoutdata)

# check if a process needs to be restarted
def checkProcess(process, processconfig, config):
    logger = config['logger']
    # let's find out the criteria to restart this process
    maxcpuusage = int(processconfig['CPURestartLevel'])
    maxmemusage = int(processconfig['MemoryRestartLevel'])
    memused = process.get_memory_info()[0]
    totalmem = psutil.virtual_memory()[0]
    mempercent = memused*100 / totalmem
    logger.info("Process %s using %f memory which is %f percent" % (process.name, memused, mempercent))

    if mempercent > maxmemusage:
        restart_process(processconfig['RestartCommand'], config)
    return


def logProcess(p, config):
    logger = config['logger']
    session = config['session']
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time))
    mem = p.get_memory_info()[0] / float(2 ** 20)
    logger.info('name %s, pid %d, start time %s, mem %d percent, cpu' % (p.name, p.pid, start_time, mem))

    for piter in config['ProcessNames']:
        # print (piter['ProcessName'])
        if piter['ProcessName'] == p.name:
            break
            print ("*** %s" % piter['ProcessName'])

    # log this process, if we are required to log all processes or
    # required to log this particular process
    if config['AllProcessLogging'] == 'Yes' or piter['ProcessLogging'] == 'Yes':
        t = ProcessTimeSeries(time = p.create_time, pid = p.pid,
            name = p.name, memusage = p.get_memory_info()[0], cpuusage = 0)
        session.add(t)
        session.commit()

        # now that we have found this process, let's remember that
        # that way, we can easily find processes that need to be restarted
        piter['FoundProcess'] = 'Yes'

    # check if we need to restart this process
    checkProcess(p, piter, config)

    return

def startProcessesNotFound(config):
    return
    # main portion of the program
    tries = 1
    while util.check_process(process_name) != util.PROCESS_RUNNING and tries <= util.MAX_RESTART_TRIES:
    	logger.error("%s is NOT running. Attempt no %d to start with %s" % (process_name, tries, process_start))
    	util.process_alert(process_name)
    	util.restart_process(process_name, process_start)
    	tries += 1

    # we have tried restarting the process multiple times now. Let's give up if still not started
    if util.check_process(process_name) != PROCESS_RUNNING:
    	# oh man
    	logger.error("%s is still not running after %d tries. Giving up..." % (process_name, MAX_RESTART_TRIES))

def iterateAllProcesses(config):
    logger = config['logger']
    count = 0

    # iterate of all processes, log them and restart them if necessary
    for p in psutil.process_iter():
        count += 1
        logProcess(p, config)
    logger.info('found a total of %d processes' % count)

# send a message if a process is not running.
def process_alert(name):
    return 0
    message = sendgrid.Mail()
    message.add_to(smtp_to)
    message.add_to(smtp_cc)
    message.set_subject("ALERT: critical process NOT running")
    message.set_html("%s is NOT running. attempting to restart it." % name)
    message.set_text("%s is NOT running. attempting to restart it." % name)
    message.set_from(smtp_from)
    status, msg = sg.send(message)
    logger.debug("sent alert message to %s with status %s and msg %s" % (smtp_to, status, msg))
