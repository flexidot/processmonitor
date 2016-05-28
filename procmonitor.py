import psutil
import time 
import sendgrid
import logging
import subprocess
import configparser
import os, sys
from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# this is where we will store our log data 
class TimeSeries(Base):
	__tablename__ = 'timeseries'
	time = Column(Float, primary_key=True)
	memusage = Column(Integer)

engine = create_engine('sqlite:///sqlalchemy_example.db')

Base.metadata.create_all(engine)
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()

# read the configuration 
config = configparser.ConfigParser()
config.read('config.json')

# setup loggin
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

process_name = config['Process']['ProcessName']
process_start = config["Process"]["ProcessStartCmd"]

smtp_password = config["SendGrid"]["APIKey"]
smtp_to = config["SendGrid"]["SmtpTo"]
smtp_from = config["SendGrid"]["SmtpFrom"]
smtp_cc = config["SendGrid"]["SmtpCc"]
sg = sendgrid.SendGridClient(smtp_password)

PROCESS_RUNNING = 0
PROCESS_NOT_RUNNING = 1

# given a command to restart a process, it runs taht command
def restart_process(name, cmd):
	stdoutdata = subprocess.getoutput(cmd)
	logger.debug(stdoutdata)

# check if a process is running, given its name. Returns either PROCESS_RUNNING or PROCESS_NOT_RUNNING
def check_process(name):

	found = 0 
	for p in psutil.process_iter():
		if p.name == process_name:
			found = 1
			break

	if found:
		mem = p.get_memory_info()[0] / float(2 ** 20)
		logger.debug("%s running, pid %d since %s, %d MB mem" % (process_name, p.pid, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time)), mem))

		t = TimeSeries(time = time.time(), memusage = mem)
		session.add(t)
		session.commit()
		return PROCESS_RUNNING
	else:
		return PROCESS_NOT_RUNNING

# send a message if a process is not running.
def process_alert(name):
	message = sendgrid.Mail()
	message.add_to(smtp_to)
	message.add_to(smtp_cc)
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

