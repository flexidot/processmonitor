import psutil
import time 
import sendgrid
import logging
import subprocess

logger = logging.getLogger('process_monitor')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('procmon.log')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch.setFormatter(formatter)

# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)


process_name = "mysqld"
process_start = "/etc/init.d/mysql restart"

smtp_host = "smtp.sendgrid.net"
smtp_port = "587"
smtp_username = "kamroot"
smtp_subject = "mail from process monitor"

PROCESS_RUNNING = 0
PROCESS_NOT_RUNNING = 1

sg = sendgrid.SendGridClient(smtp_password)

def restart_process(name, cmd):
	stdoutdata = subprocess.getoutput(cmd)
	logger.debug(stdoutdata)

def check_process(name):

	found = 0 
	for p in psutil.process_iter():
		if p.name == process_name:
			found = 1
			break

	if found:
		logger.debug("%s is running with pid %d started at %s" % (process_name, p.pid, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time))))
		return PROCESS_RUNNING
	else:
		return PROCESS_NOT_RUNNING

def process_alert(name):
	message = sendgrid.Mail()
	message.add_to(smtp_to)
	message.set_subject("ALERT: critical process NOT running")
	message.set_html("%s is NOT running. attempting to restart it." % name)
	message.set_text("%s is NOT running. attempting to restart it." % name)
	message.set_from(smtp_from)
	status, msg = sg.send(message)
	logger.debug("sent alert message to %s with status %s and msg %s" % (smtp_to, status, msg))

# main portion of the program

MAX_RESTART_TRIES = 3
tries = 1
while check_process(process_name) != PROCESS_RUNNING and tries <= MAX_RESTART_TRIES:
	logger.error("%s is NOT running. Attempt no %d to start with %s" % (process_name, tries, process_start))
	process_alert(process_name)
	restart_process(process_name, process_start)
	tries += 1

# we have tried restarting the process multiple times now. Let's give up if still not started
if check_process(process_name) != PROCESS_RUNNING:
	# oh man
	logger.error("%s is still not running after %d tries. Giving up..." % (process_name, MAX_RESTART_TRIES))

