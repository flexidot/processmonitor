import os, sys
from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

def getSession(config):
	logger = config['logger']
	engine = create_engine(config['DBLogFile'])
	Base.metadata.create_all(engine)
	# Bind the engine to the metadata of the Base class so that the
	# declaratives can be accessed through a DBSession instance
	Base.metadata.bind = engine

	DBSession = sessionmaker(bind=engine)
	session = DBSession()
	logger.debug('Returning session')
	config['session'] = session
	return session

# this is where we will store our log data
class ProcessTimeSeries(Base):
	__tablename__ = 'processtimeseries'
	id = Column(Integer, primary_key=True)
	name = Column(String)
	pid = Column(Integer)
	time = Column(Float, unique = False)
	cpuusage = Column(Integer)
	memusage = Column(Integer)

class ProcessRestart(Base):
	__tablename__ = 'processrestart'
	id = Column(Integer, primary_key = True)
	name = Column(String)
	time = Column(Float, unique = False)
	reason = Column(Integer)
