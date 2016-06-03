import sendgrid
import util, configparser, getopt, subprocess, sys, time, psutil
from models import ProcessTimeSeries, getSession

start_time = time.time()

# initial setup
config = util.readConfig()
logger = util.getLogger(config)
sg = util.getSendGrid(config)
session = getSession(config)

# parse arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hvr", ["--restarts"])
except getopt.GetoptError:
    print ("Not enough options")
    sys.exit(2)

for opt, arg in opts:
    if opt == '-h':
        util.printhelp()
        sys.exit(0)
    elif opt in ("-r", "--restarts"):
        util.printrestarts(config)
    elif opt == "-v":
        util.printversion()

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

# save the data base
session.commit()
exit(0)
