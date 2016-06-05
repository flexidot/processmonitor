import os, sys, datetime, time
from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from uptime import uptime
from sqlalchemy import create_engine
from uptime import boottime

Base = declarative_base()

class ProcessID(Base):
	__tablename__ = "processid"
	pguid = Column(String, primary_key = True)
	name = Column(String)
	pid = Column(Integer)
	timestarted = Column(Integer, unique = False)

	processtimeseries = relationship('ProcessTimeSeries',
		back_populates = 'processID', cascade="all, delete, delete-orphan")

# this is where we will store our log data
class ProcessTimeSeries(Base):
	__tablename__ = 'processtimeseries'
	id = Column(Integer, primary_key=True)
	pguid = Column(String, ForeignKey(ProcessID.pguid))
	time = Column(Float, unique = False)
	cpuusage = Column(Integer)
	memusage = Column(Integer)

	processID = relationship('ProcessID', back_populates="processtimeseries")

class ProcessRestart(Base):
	__tablename__ = 'processrestart'
	id = Column(Integer, primary_key = True)
	name = Column(String)
	time = Column(Float, unique = False)
	reason = Column(Integer)

class Database():
	def getSession(self, config):
		logger = config['logger']
		engine = create_engine(config['DBLogFile'])
		Base.metadata.create_all(engine)
		# Bind the engine to the metadata of the Base class so that the
		# declaratives can be accessed through a DBSession instance
		Base.metadata.bind = engine

		DBSession = sessionmaker(bind=engine)
		session = DBSession()
		logger.debug('Returning session')
		return session

	def __init__(self, config):
		self.session = self.getSession(config)
		config['session'] = self.session
		self.config = config
		config['db'] = self

	# pguid is a process guid that is unique across reboots. Uses boottime as
	# part of GUID
	def getPGUID(self, process):
		b = boottime()
		assert(b != None)

		pguid = str(process.pid) + '.' + str(b)
		# save the guid. if it does not exist in the db, it will be created
		self.savePGUID(process, pguid)
		self.config['logger'].debug('Returning guid %s for process %s with pid %d' %
			(pguid, process.name, process.pid))
		return pguid

	def savePGUID(self, process, pguid):
		for pg in self.session.query(ProcessID).all():
			if pg.pguid == pguid:
				self.config['logger'].debug('Found pguid for %s' % pguid)
				return
		pg = ProcessID(pguid = pguid, name = process.name, pid = process.pid,
			timestarted = process.create_time)
		self.session.add(pg)

	def logTimeSeries(self, p, config):
		logger = config['logger']
		pguid = self.getPGUID(p)
		tm = time.mktime(datetime.datetime.utcnow().timetuple())
		t = ProcessTimeSeries(time = tm,
			memusage = p.get_memory_info()[0], cpuusage = 0)
		t.pguid = pguid
		self.session.add(t)
		logger.debug('Adding time series for process %s' % p.name)

	def addRestartEvent(self, config, time, name, reason):
		logger = config['logger']
		restartlog = ProcessRestart(time = time, name = name,
			reason = reason)
		self.session.add(restartlog)
		logger.debug('Adding restart event for process %s' % name)

	def getRestarts(self):
		return self.session.query(ProcessRestart).all()

	def getProcessTimeSeries(self):
			return self.session.query(ProcessTimeSeries).all()

	def getProcessIDs(self):
		return self.session.query(ProcessID).all()

	def finalize(self):
		self.session.commit()
