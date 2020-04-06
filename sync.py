import peewee
import models
import sched
import time
import sys

from models.BaseModelMail import db as mail_db
from models.BaseModelCanaries import db as canary_db

debug = True

###############
#   Helpers   #
###############


def log(message):
    if debug:
        print('[DEBUG]: %s' % message)


def printHelp():
    print(
        'Please run sync.py with a parameter:\n~$ sync.py {parameter}\n\t-s\tSetup basic server environment\n\t-d\tRun in daemon mode - automatically check and sync canaries')
    exit(1)


#############
#   SETUP   #
#############


def setup():
    log('Setup time!')
    print(
        'Please check your configuration. Are you sure to continue? [y/N] ', end='')
    if str(input()).lower() in ('y', 'yes'):
        print('Creating model tables for Canaries Server')
        try:
            mail_db.connect()
            mail_db.create_tables(
                [models.VirtualAlias, models.VirtualDomain, models.VirtualUser])
            mail_db.close()
        except Exception as e:
            print('An error occured while creating tables!')
            log(e)
        log('Done')
    else:
        exit


##############
#   DAEMON   #
##############


def daemon():
    log('Starting canary sync daemon service')
    # setup scheduler
    s = sched.scheduler(time.time, time.sleep)


########################
#   Argument parsing   #
########################

# not enough parameters supplied - show help
if len(sys.argv) < 2:
    printHelp()

# if the option to trigger setup was called
if '-s' in sys.argv:
    setup()

# if the option to start the sync service as daemon was called
elif '-d' in sys.argv:
    daemon()

# unsupported option
else:
    log('Command not supported\n')
    printHelp()
