import peewee
import models
import sched
import time
import sys
from termcolor import colored, cprint
import os
import getpass
import json
from crypt import crypt
from hashlib import sha1
import datetime

from models.BaseModelMail import db as mail_db
from models.BaseModelCanaries import db as canary_db

debug = False

###############
#   Helpers   #
###############


def log(message):
    if debug:
        cprint('[DEBUG]: %s' % message, 'yellow')


def error(message):
    cprint('[ERROR]: %s' % message, 'white', 'on_red')


def printHelp():
    cprint(
        'Please run sync.py with a parameter:\n~$ python3 ./sync.py {parameter}\n\
            \t-s\tSetup basic server environment\n\
            \t-d\tRun in daemon mode - automatically check and sync canaries', 'cyan')
    exit(1)


#############
#   SETUP   #
#############


def setup():
    log('Setup time!')

    # Open configuration file
    try:
        with open('config.json', encoding='utf8') as config_file:
            Config = json.load(config_file)
    except:
        print('Unable to open config.json!')
        print('If you haven\'t created a configuration file, please use the example configuration file as a guide.')
        print('Otherwise, make sure the file permissions are set correctly.')
        exit(1)

    #
    # Check if the script is ran by root
    #
    if getpass.getuser() != 'root':
        error('Please run the script as root! Current user: %s' %
              getpass.getuser())
        exit(1)

    #
    # Ask the user if they set-up the configuration
    #

    cprint(
        'Please check your configuration. Are you sure to continue? [y/N] ', 'magenta', end='')

    if str(input()).lower() not in ('y', 'yes'):
        print('Cancelling...')
        exit

    #
    # Create table structure in the server database
    #

    print('Creating database model tables for Canary Server...')
    log('Connecting to Canary Server database...')
    try:
        if mail_db.is_closed():
            mail_db.connect()
        log('Creating tables for VirtualAlias, VirtualDomain & VirtualUser...')
        mail_db.create_tables(
            [models.VirtualAlias, models.VirtualDomain, models.VirtualUser])
    except Exception as e:
        error('An error occured while creating tables!')
        log(e)
        exit(1)
    finally:
        mail_db.close()
        log('Connection closed.')
    print('Done.')

    #
    # Check if the script is ran on linux
    #

    if sys.platform != "linux" and sys.platform != "linux2":
        error('Rest of the configuration is not designed for Windows operating systems!')
        exit(1)

    #
    # Ask the user if they want to auto-create folder structure for Dovecot based on domains from the backend database
    #

    cprint(
        'Do you want to create virtual domain folders in /var/mail/vhosts/? [y/N] ', 'magenta', end='')

    domains = None

    if str(input()).lower() in ('y', 'yes'):
        # get vmail GID and UID
        uid = os.stat('/var/mail/').st_uid
        gid = os.stat('/var/mail/').st_gid

        #
        # Get all domains from backend
        #

        print('Pulling domain configuration from backend...')
        log('Connecting to Canary Backend database...')
        try:
            if canary_db.is_closed():
                canary_db.connect()
            log('Getting domain configuration...')
            domains = models.Domain.select()
        except Exception as e:
            error('An error occured while getting data!')
            log(e)
            exit(1)
        finally:
            canary_db.close()
            log('Connection closed.')
        print('Done.')

        #
        # Create the vhosts folder and domain folders with the right permissions
        #

        print('Setting up virtual domain folders...')

        try:
            if not os.path.exists('/var/mail/vhosts/') or not os.path.isdir('/var/mail/vhosts/'):
                log('Creating vhosts folder...')
                os.makedirs('/var/mail/vhosts/', mode=0o770, exist_ok=True)
                os.chown('/var/mail/vhosts/', uid, gid)

            for domain in domains:
                path = '/var/mail/vhosts/%s' % domain.domain
                if not os.path.exists(path) or not os.path.isdir(path):
                    log('Directory for %s does not exist. Creating...' %
                        domain.domain)
                    os.makedirs(path, mode=0o770, exist_ok=True)
                    os.chown(path, uid, gid)
        except Exception as e:
            error('An error occured while creating folders!')
            log(e)
            exit(1)

        print('Done.')

    #
    # Ask the user if they want to sync the email accounts from backend
    #

    cprint(
        'Do you want to synchronize Canary Server now? [y/N] ', 'magenta', end='')

    if str(input()).lower() in ('y', 'yes'):
        print('Synchronizing current configuration and accounts from Canary Backend...')

        #
        # Get all domains from backend
        #

        domain_mapping = dict()

        if not domains:
            print('Pulling domain configuration from backend...')
            log('Connecting to Canary Backend database...')
            try:
                if canary_db.is_closed():
                    canary_db.connect()
                log('Getting domain configuration...')
                domains = models.Domain.select()
            except Exception as e:
                error('An error occured while getting domains!')
                log(e)
                exit(1)
            finally:
                canary_db.close()
                log('Connection closed.')
            print('Done.')

        #
        # Add all new domains to the virtual_domains table
        #

        print('Adding virtual domains...')
        log('Connecting to Canary Server database...')
        try:
            if mail_db.is_closed():
                mail_db.connect()

            for domain in domains:
                try:
                    d = models.VirtualDomain(name=domain.domain)
                    d.save()
                    log('Adding %s' % domain.domain)
                    domain_mapping[domain.uuid] = d.id
                except peewee.IntegrityError:
                    log('Skipping %s - already exists' % domain.domain)
                    d = models.VirtualDomain.get(
                        models.VirtualDomain.name == domain.domain)
                    domain_mapping[domain.uuid] = d.id
                    pass
                except:
                    raise
        except Exception as e:
            error('An error occured while adding virtual domains!')
            log(e)
            exit(1)
        finally:
            mail_db.close()
            log('Connection closed.')
        print('Done.')

        #
        # Get all canary accounts from backend
        #

        print('Pulling canary configuration from backend...')
        log('Connecting to Canary Backend database...')
        try:
            if canary_db.is_closed():
                canary_db.connect()
            log('Getting canary accounts...')
            canaries = models.Canary.select()
        except Exception as e:
            error('An error occured while getting canaries!')
            log(e)
            exit(1)
        finally:
            canary_db.close()
            log('Connection closed.')
        print('Done.')

        #
        # Add all new canary accounts to the virtual_users table
        #

        print('Adding virtual users...')
        log('Connecting to Canary Server database...')
        try:
            if mail_db.is_closed():
                mail_db.connect()

            for canary in canaries:
                try:
                    u = models.VirtualUser(
                        domain_id=domain_mapping[canary.domain], email=canary.email, password=crypt(canary.password, '$6$%s' % str(sha1(os.urandom(32)).hexdigest())[0:16]))
                    u.save()
                    log('Adding %s' % canary.email)
                except peewee.IntegrityError:
                    log('Skipping %s - already exists' % canary.email)
                    pass
                except:
                    raise

        except Exception as e:
            error('An error occured while adding virtual domains!')
            log(e)
            exit(1)
        finally:
            mail_db.close()
            log('Connection closed.')
        print('Done.')

    print('Configuration finished!')
    exit


##############
#   DAEMON   #
##############


def daemon(delay):
    log('Daemon time!')
    print('Starting Canary Server sync daemon service...')

    # setup scheduler
    s = sched.scheduler(time.time, time.sleep)
    s.enter(delay, 1, sync, (s, delay))
    s.run()


def sync(sc, delay):
    print('[%s] Running...' %
          datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    sc.enter(delay, 1, sync, (sc, delay))


########################
#   Argument parsing   #
########################


# not enough parameters supplied - show help
if len(sys.argv) < 2:
    printHelp()

# enable debugging
if '--debug' in sys.argv:
    debug = True

# if the option to trigger setup was called
if '-s' in sys.argv:
    setup()

# if the option to start the sync service as daemon was called
elif '-d' in sys.argv:
    delay = 60
    if len(sys.argv) > 2 and sys.argv[2].isnumeric():
        delay = int(sys.argv[2])
    daemon(delay)

# unsupported option
else:
    log('Command not supported\n')
    printHelp()
