import peewee
import models
import sched
import time
import sys

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
