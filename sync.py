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
from mailparser import MailParser

from models.BaseModelMail import db as mail_db
from models.BaseModelCanaries import db as canary_db

debug = False
parser = None


###############
#   Helpers   #
###############


def log(message, prefix=''):
    if debug:
        cprint('%s[DEBUG]: %s' % (prefix, message), 'yellow')


def error(message, color=False):
    if color:
        cprint('[ERROR]: %s' % message, 'white', 'on_red')
    else:
        print('[canary-server][ERROR]: %s' % message, file=sys.stderr)


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
        error('Unable to open config.json!\n\
            If you haven\'t created a configuration file, please use the example configuration file as a guide.\n\
            Otherwise, make sure the file permissions are set correctly.', Trues)
        exit(1)

    #
    # Check if the script is ran by root
    #
    if getpass.getuser() != 'root':
        error('Please run the script as root! Current user: %s' %
              getpass.getuser(), True)
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
    try:
        if mail_db.is_closed():
            log('Connecting to Canary Server database...')
            mail_db.connect()
        log('Creating tables for VirtualAlias, VirtualDomain & VirtualUser...')
        mail_db.create_tables(
            [models.VirtualAlias, models.VirtualDomain, models.VirtualUser])
    except Exception as e:
        error('An error occured while creating tables!', True)
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
        error(
            'Rest of the configuration is not designed for Windows operating systems!', True)
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
        try:
            if canary_db.is_closed():
                log('Connecting to Canary Backend database...')
                canary_db.connect()
            log('Getting domain configuration...')
            domains = models.Domain.select()
        except Exception as e:
            error('An error occured while getting data!', True)
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
            error('An error occured while creating folders!', True)
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

        # domain to uuid mapping
        domain_mapping = dict()

        if not domains:
            print('Pulling domain configuration from backend...')
            try:
                if canary_db.is_closed():
                    log('Connecting to Canary Backend database...')
                    canary_db.connect()
                log('Getting domain configuration...')
                domains = models.Domain.select()
            except Exception as e:
                error('An error occured while getting domains!', True)
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
        try:
            if mail_db.is_closed():
                log('Connecting to Canary Server database...')
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
            error('An error occured while adding virtual domains!', True)
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
        try:
            if canary_db.is_closed():
                log('Connecting to Canary Backend database...')
                canary_db.connect()
            log('Getting canary accounts...')
            canaries = models.Canary.select()
        except Exception as e:
            error('An error occured while getting canaries!', True)
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
        try:
            if mail_db.is_closed():
                log('Connecting to Canary Server database...')
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
            error('An error occured while adding virtual domains!', True)
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
    global parser

    log('Daemon time!', prefix='[canary-server]')
    print('Starting Canary Server sync daemon service...')

    # setup MailParser
    parser = MailParser()

    # setup scheduler
    s = sched.scheduler(time.time, time.sleep)
    sync(s, delay)
    s.run()


def sync(sc, delay):
    global parser

    maildirs = []

    print('Checking for changes...')
    log('[%s] Checking for changes...' %
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), prefix='[canary-server]')

    # domain to uuid mapping
    domain_mapping = dict()

    print('Pulling domain configuration from backend...')
    try:
        if canary_db.is_closed():
            log('Connecting to Canary Backend database...',
                prefix='[canary-server]')
            canary_db.connect()
        if mail_db.is_closed():
            log('Connecting to Canary Server database...',
                prefix='[canary-server]')
            mail_db.connect()

        log('Getting domain configuration...', prefix='[canary-server]')
        domains = models.Domain.select()

        print('Checking for new domains...')
        log('Adding new domains...', prefix='[canary-server]')
        for domain in domains:
            try:
                d = models.VirtualDomain(name=domain.domain)
                d.save()
                print('Adding %s' % domain.domain)
                domain_mapping[domain.uuid] = [d.id, domain.domain]
            except peewee.IntegrityError:
                log('Skipping %s - already exists' %
                    domain.domain, prefix='[canary-server]')
                d = models.VirtualDomain.get(
                    models.VirtualDomain.name == domain.domain)
                domain_mapping[domain.uuid] = [d.id, domain.domain]
                pass
            except:
                raise

        print('Checking for new canaries...')

        log('Getting canary accounts...', prefix='[canary-server]')
        canaries = models.Canary.select()

        for canary in canaries:
            try:
                maildirs.append('/var/mail/vhosts/%s/%s/' %
                                (domain_mapping[canary.domain][1], str(canary.email).split('@')[0]))

                u = models.VirtualUser(
                    domain_id=domain_mapping[canary.domain][0], email=canary.email, password=crypt(canary.password, '$6$%s' % str(sha1(os.urandom(32)).hexdigest())[0:16]))
                u.save()
                log('Adding %s' % canary.email, prefix='[canary-server]')
            except peewee.IntegrityError:
                log('Skipping %s - already exists' %
                    canary.email, prefix='[canary-server]')
                pass
            except:
                raise

    except Exception as e:
        error('An error occured while getting domains!')
        error(e)
    finally:
        canary_db.close()
        mail_db.close()
        log('Connection closed.', prefix='[canary-server]')

    print('Done.')

    print(maildirs)

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
