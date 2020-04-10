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
import uuid
import logging
import logging.handlers

from models.BaseModelMail import db as mail_db
from models.BaseModelCanaries import db as canary_db

debug = False
parser = None
Config = None

logger = logging.getLogger('canary-server')
handler = logging.handlers.SysLogHandler(address='/dev/log')
handler.setFormatter(logging.Formatter(
    '%(name)s: [%(levelname)s] %(message)s'
))
logger.addHandler(handler)


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
        error('Unable to open config.json!\n\
            If you haven\'t created a configuration file, please use the example configuration file as a guide.\n\
            Otherwise, make sure the file permissions are set correctly.')
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
    try:
        if mail_db.is_closed():
            log('Connecting to Canary Server database...')
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
        error(
            'Rest of the configuration is not designed for Windows operating systems!')
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
        try:
            if canary_db.is_closed():
                log('Connecting to Canary Backend database...')
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
    global parser, Config, logger

    # Open configuration file
    try:
        with open('config.json', encoding='utf8') as config_file:
            Config = json.load(config_file)
    except:
        logger.error('Unable to open config.json!\n\
            If you haven\'t created a configuration file, please use the example configuration file as a guide.\n\
            Otherwise, make sure the file permissions are set correctly.')
        exit(1)

    logger.debug('Daemon time!')
    logger.info('Starting Canary Server sync daemon service...')

    # setup MailParser
    parser = MailParser()

    # setup scheduler
    s = sched.scheduler(time.time, time.sleep)
    sync(s, delay)
    s.run()


def sync(sc, delay):
    global parser, Config

    maildirs = []

    logger.info('Checking for changes...')
    logger.debug('[%s] Checking for changes...' %
                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # domain to uuid mapping
    domain_mapping = dict()

    logger.info('Pulling domain configuration from backend...')
    try:
        if canary_db.is_closed():
            logger.debug('Connecting to Canary Backend database...')
            canary_db.connect()
        if mail_db.is_closed():
            logger.debug('Connecting to Canary Server database...')
            mail_db.connect()

        logger.debug('Getting domain configuration...')
        domains = models.Domain.select()

        logger.info('Checking for new domains...')
        logger.debug('Adding new domains...')
        for domain in domains:
            try:
                d = models.VirtualDomain(name=domain.domain)
                d.save()
                logger.info('Adding %s' % domain.domain)
                domain_mapping[domain.uuid] = [d.id, domain.domain]
            except peewee.IntegrityError:
                logger.debug('Skipping %s - already exists' %
                             domain.domain)
                d = models.VirtualDomain.get(
                    models.VirtualDomain.name == domain.domain)
                domain_mapping[domain.uuid] = [d.id, domain.domain]
                pass
            except:
                raise

        logger.info('Checking for new canaries...')

        logger.debug('Getting canary accounts...')
        canaries = models.Canary.select()

        for canary in canaries:
            try:
                maildirs.append(['%s%s/%s/' %
                                 (Config['maildir'], domain_mapping[canary.domain][1], str(canary.email).split('@')[0]), canary.uuid])

                u = models.VirtualUser(
                    domain_id=domain_mapping[canary.domain][0], email=canary.email, password=crypt(canary.password, '$6$%s' % str(sha1(os.urandom(32)).hexdigest())[0:16]))
                u.save()
                logger.info('Adding %s' % canary.email)
            except peewee.IntegrityError:
                logger.debug('Skipping %s - already exists' %
                             canary.email)
                pass
            except:
                raise

        logger.info('Checking for new mail...')

        logger.debug('Getting messages from maildirs...')

        try:
            for maildir in maildirs:
                mail = parser.getMail(maildir[0])
                if len(mail):
                    logger.info('Mailbox %s has %s new messages.' %
                                (maildir[0], len(mail)))
                else:
                    logger.debug('Mailbox %s has %s new messages.' %
                                 (maildir[0], len(mail)))
                for m in mail:
                    models.Mail(uuid=uuid.uuid4(),
                                canary=maildir[1], received_on=m['date'], mail_from=m['sender'], subject=m['subject'], body=m['body']).save()
        except Exception as e:
            logger.warning('An error occured while parsing maildirs!')
            logger.warning(e)

    except Exception as e:
        logger.warning('An error occured while getting domains!')
        logger.warning(e)
    finally:
        canary_db.close()
        mail_db.close()
        logger.debug('Connection closed.')

    logger.info('Done.')

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
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

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
