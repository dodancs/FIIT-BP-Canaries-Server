# FIIT BP Canaries - Server

This repository holds source codes for the server portion of the Leak-detection system

## Contains

- Linux configuration
- Postfix configuration
- Dovecot configuration
- Syslog configuration
- Canary & mail sync service setup & configuration

## Canary Sync service

- [sync.py](sync.py)
- [Data models](models/)
  - [Virtual domains](schema/virtual-domains.sql)
  - [Virtual users](schema/virtual-users.sql)
  - [Virtual aliases](schema/virtual-aliases.sql)
- [Example configuration](config.example.json)

## Prerequisites

- Ubuntu server 16.04 or higher
- MySQL server / database
- IPTables firewall
- Python >= 3.5.X _(incompatible with Python 2.X.X)_



## Installing & configuring Redis log server

### Installing required packages

```bash
~$ sudo apt install redis-server
~$ sudo apt install syslog-ng
~$ sudo apt install syslog-ng-mod-redis # Redis module should be installed automatically
```



### Configuring Redis server

Here are the parameters that need to be changed in the Redis config file (usually `/etc/redis.conf` or `/etc/redis/redis.conf`):

```ini
bind 0.0.0.0 # set the socket to accept connections from any IP not only localhost
```

You may also change other parameters to suite your configuration. The configuration file is well documented: [Redis 3.0 configuration](https://raw.githubusercontent.com/antirez/redis/3.0/redis.conf).



### Configuring IPTables firewall

```bash
~$ sudo iptables -I INPUT -i [INTERFACE] -p tcp -m tcp --dport 6379 -s [IP] -j ACCEPT
~$ sudo iptables -P INPUT DROP
~$ sudo iptables -P FORWARD DROP
~$ sudo iptables -P OUTPUT ACCEPT
~$ sudo iptables -A INPUT -i lo -j ACCEPT
~$ sudo iptables -A OUTPUT -o lo -j ACCEPT
~$ sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
```

The first rule allows to reach Redis only from a specific IP address which is the address of the Canary Expert(s). Next set of three rules sets that any incoming traffic will be blocked and any output will be let through the firewall. The next two rules allow communication on local loopback interface. The last rule allows already established traffic through the firewall.

This configuration ensures that no one, but Canary Experts can communicate with the Redis database.

_NOTE: With newer versions of syslog-ng, you may specify `auth([PASSWORD])` parameter in the destination configuration and `requirepass [PASSWORD]` parameter in the Redis configuration to protect the Redis server with a password instead of IPTables._



### Configuring Syslog-ng

Create a new file in `/etc/syslog-ng/conf.d/`:

```bash
~$ touch /etc/syslog-ng/conf.d/canaries.conf
```

Open the file in your favourite editor and insert the following lines:

```ini
# Configure Redis destination
destination d_redis {
    redis(
        host("localhost")
        port(6379)
        command("rpush" "log_queue" "{\"time\":${UNIXTIME}, \"message\":\"${MESSAGE}\", \"program\":\"${PROGRAM}\"}")
    );
};

# Setup filters for postfix and dovecot logs
filter f_dovecot { program("^dovecot$"); };
filter f_postfix { program("^postfix/") or program("^postgrey"); };

# Enable logging of postfix and dovecot to Redis
log { source(s_sys); filter(f_dovecot); destination(d_redis); };
log { source(s_sys); filter(f_postfix); destination(d_redis); };
```

Check the `/etc/syslog-ng/syslog-ng.conf` to find the system log source. It should look something like this:

```ini
########################
# Sources
########################
# This is the default behavior of sysklogd package
# Logs may come from unix stream, but not from another machine.
#
source s_src {
       system();
       internal();
};
```

Change the name of the source in the configuration file we created earlier to match the name in the main configuration:

```ini
# Enable logging of postfix and dovecot to Redis
log { source(s_src); filter(f_dovecot); destination(d_redis); };
log { source(s_src); filter(f_postfix); destination(d_redis); };
```



### Restart and enable services

```bash
# Restart services to load configuration changes
~$ systemctl restart redis-server
~$ systemctl restart syslog-ng
# Make sure the services start on boot
~$ systemctl enable redis-server
~$ systemctl enable syslog-ng
```



## Installing & configuring mail honeypot

### Installing required packages

```bash
~$ sudo apt update
~$ sudo apt install postfix postfix-mysql
~$ sudo apt install dovecot-core dovecot-imapd dovecot-lmtpd dovecot-mysql
~$ sudo apt install python3-pip
~$ sudo apt install git
```



### Configuring Postfix

Backup the existing configuration files:

```bash
~$ cd /etc/postfix/
/etc/postfix/$ cp main.cf main.cf.bak
/etc/postfix/$ cp master.cf master.cf.bak
```

Change the `main.cf` configuration to look like this:

```ini
myhostname = [YOUR DOMAIN NAME]
myorigin = [YOUR DOMAIN NAME]
mydestination = localhost
relay_domains = *
append_dot_mydomain = no
inet_protocols = ipv4
inet_interfaces = all

smtpd_banner = $myhostname
biff = no

mailbox_command = /usr/lib/dovecot/deliver -f "$SENDER" -a "$RECIPIENT"

default_privs = nobody

smtp_tls_security_level = may
smtp_tls_loglevel = 1
smtpd_tls_security_level = may
smtpd_use_tls = yes
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
smtpd_tls_cert_file = [SSL CERTIFICATE PATH]
smtpd_tls_key_file = [SSL CERTIFICATE KEY PATH]

message_size_limit = 1024000
mailbox_size_limit = 1024000

alias_maps = hash:/etc/aliases
alias_database = hash:/etc/aliases

virtual_mailbox_domains = mysql:/etc/postfix/mysql/virtual-mailbox-domains.cf
virtual_mailbox_maps = mysql:/etc/postfix/mysql/virtual-mailbox-maps.cf
virtual_alias_maps = mysql:/etc/postfix/mysql/virtual-alias-maps.cf,
                     mysql:/etc/postfix/mysql/virtual-email2email.cf
virtual_transport = lmtp:unix:private/dovecot-lmtp

# Block all outgoing mail
default_transport = error: Please check your e-mail configuration
```

Create a directory for the virtual configuration and the four configuration files:

```bash
~$ cd /etc/postfix/
/etc/postfix/$ mkdir mysql; cd mysql
/etc/postfix/mysql$ touch virtual-mailbox-domains.cf
/etc/postfix/mysql$ touch virtual-mailbox-maps.cf
/etc/postfix/mysql$ touch virtual-alias-maps.cf
/etc/postfix/mysql$ touch virtual-email2email.cf
```

At top of each configuration file, add the following lines, that specify the connection to MySQL server:

```ini
user = [DB USER]
password = [DB PASSWORD]
hosts = [DB HOST]
dbname = [DB DATABASE]
```

Add appropriate SQL queries to each file:

**virtual-mailbox-domains.cf**

```ini
query = SELECT destination FROM virtual_aliases WHERE source='%s'
```

**virtual-mailbox-maps.cf**

```ini
query = SELECT 1 FROM virtual_users WHERE email='%s'
```

**virtual-alias-maps.cf**

```ini
query = SELECT destination FROM virtual_aliases WHERE source='%s'
```

**virtual-email2email.cf**

```ini
query = SELECT email FROM virtual_users WHERE email='%s'
```

Reset directory permissions:

```bash
~$ chmod -R o-rwx /etc/postfix
```

Change the `master.cf` configuration to look like this:

```ini
smtp       inet  n       -       y       -       -       smtpd
#smtp      inet  n       -       y       -       1       postscreen
#smtpd     pass  -       -       y       -       -       smtpd
#dnsblog   unix  -       -       y       -       0       dnsblog
#tlsproxy  unix  -       -       y       -       0       tlsproxy
submission inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_reject_unlisted_recipient=no
  -o smtpd_client_restrictions=$mua_client_restrictions
  -o smtpd_helo_restrictions=$mua_helo_restrictions
  -o smtpd_sender_restrictions=$mua_sender_restrictions
  -o smtpd_recipient_restrictions=
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
smtps     inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_reject_unlisted_recipient=no
  -o smtpd_client_restrictions=$mua_client_restrictions
  -o smtpd_helo_restrictions=$mua_helo_restrictions
  -o smtpd_sender_restrictions=$mua_sender_restrictions
  -o smtpd_recipient_restrictions=
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
...
```



### Configuring Dovecot

Open the Dovecot configuration file (`/etc/dovecot/dovecot.conf`) in your favourite editor.

In the `Enable installed protocols` section, comment out the existing line and add the following line:

```ini
# Enable installed protocols
#!include_try /usr/share/dovecot/protocols.d/*.protocol
protocols = imap lmtp
```

We aren't going to enable POP3 protocol, as we want all the emails to stay on the server.

To be able to collect the log information we need for Canary Experts, we need to enable the following settings in `/etc/dovecot/conf.d/10-logging.conf`:

```ini
auth_verbose = yes
auth_verbose_passwords = yes
auth_debug = yes
auth_debug_passwords = yes
mail_debug = yes
```

In the `/etc/dovecot/conf.d/10-mail.conf` file, we are going to change two lines of code, to change the mail storage destination:

```ini
...
mail_location = maildir:/var/mail/vhosts/%d/%n
...
mail_privileged_group = vmail
...
```

Add a system user account for handling mail:

```bash
~$ sudo groupadd -g 5000 vmail
~$ sudo useradd -g vmail -u 5000 vmail -d /var/mail/
~$ sudo chown -R vmail:vmail /var/mail/
```

Edit the authentication configuration `/etc/dovecot/conf.d/10-auth.conf`:

```ini
...
disable_plaintext_auth = no
...
auth_mechanisms = plain login
...
!include auth-system.conf.ext
...
!include auth-sql.conf.ext
...
```

In `/etc/dovecot/conf.d/auth-sql.conf.ext`:

```ini
...
passdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}
...
userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}
...
```

Add database configuration:

```bash
~$ touch /etc/dovecot/dovecot-sql.conf.ext
```

Add these lines and change your database details:

```ini
driver = mysql
connect = host=[DB HOST] dbname=[DB DATABASE] user=[DB USER] password=[DB PASSWORD]
default_pass_scheme = SHA512-CRYPT
password_query = SELECT email as user, password FROM virtual_users WHERE email='%u';
```

Edit the master configuration file `/etc/dovecot/conf.d/10-master.conf`:

```ini
...
service imap-login {
  inet_listener imap {
    port = 0
  }
  inet_listener imaps {
    port = 993
    ssl = yes
  }
  ...
}
...
service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
...
}
...
service auth {
  ...
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }

  unix_listener auth-userdb {
    mode = 0600
    user = vmail
  }
...
  user = dovecot
}
...
service auth-worker {
  ...
  user = vmail
}
...
```

Update the SSL configuration file `/etc/dovecot/conf.d/10-ssl.conf`. Add SSLv3 support and set the certificate:

```ini
...
# SSL/TLS support: yes, no, required. <doc/wiki/SSL.txt>
ssl = required
...
ssl_cert = <[SSL CERTIFICATE PATH]
ssl_key = <[SSL CERTIFICATE KEY PATH]
...
# SSL protocols to use
ssl_protocols = !SSLv2 !SSLv3

# SSL ciphers to use
ssl_cipher_list = ALL:!LOW:!SSLv2:!SSLv3:!EXP:!aNULL
```

As last, update folder permissions:

```bash
~$ sudo chown -R vmail:dovecot /etc/dovecot
~$ sudo chmod -R o-rwx /etc/dovecot
```



### Configuring IPTables firewall

If the firewall configuration from previous steps is used, be sure to add rules to allow SMTP and IMAP communication through:

```bash
~$ sudo iptables -I INPUT -i [INTERFACE] -p tcp -m tcp --dport 25 -j ACCEPT
~$ sudo iptables -I INPUT -i [INTERFACE] -p tcp -m tcp --dport 465 -j ACCEPT
~$ sudo iptables -I INPUT -i [INTERFACE] -p tcp -m tcp --dport 143 -j ACCEPT
~$ sudo iptables -I INPUT -i [INTERFACE] -p tcp -m tcp --dport 993 -j ACCEPT
```



### <a name="sync-service"></a>Setting up sync service

Download the repository code:

```bash
~$ cd /opt/
/opt/$ git clone git@github.com:dodancs/FIIT-BP-Canaries-Server.git
```

Create a configuration file:

```bash
/opt/$ cd FIIT-BP-Canaries-Server/
/opt/FIIT-BP-Canaries-Server/$ cp config.example.json config.json
```

Open the `config.json` file in your favourite editor and change the settings to match your configuration:

```json
{
  "canary": {
    "db_host": "host",
    "db_port": 3306,
    "db_user": "user",
    "db_password": "password",
    "db_db": "database",
    "db_charset": "utf8mb4"
  },
  "mail": {
    "db_host": "host",
    "db_port": 3306,
    "db_user": "user",
    "db_password": "password",
    "db_db": "database",
    "db_charset": "utf8mb4"
  }
}
```

There are two database configurations. The first one called `canary` is the database for Canary Backend. The second one (`mail`) is for the Canary Server.

Now, you need to install all the required Python packages. **If you want to use a virtual environment for this code, run the code below.** Otherwise only install the required packages to your whole system with `pip3 install -r ./requirements.txt`.

```bash
/opt/FIIT-BP-Canaries-Server/$ sudo pip3 install virtualenv
/opt/FIIT-BP-Canaries-Server/$ python3 -m virtualenv [ENVIRONMENT NAME]
/opt/FIIT-BP-Canaries-Server/$ source ./[ENVIRONMENT NAME]/bin/activate
([ENVIRONMENT NAME]) /opt/FIIT-BP-Canaries-Server/$
```

Install Python requirements (_after activating the environment, if wanted_):

```bash
/opt/FIIT-BP-Canaries-Server/$ pip3 install -r ./requirements.txt
```



### Configuring database

First, we need to create the MySQL tables for our virtual users, domains and aliases.

To do this, [setup Canary Backend sync service](#sync-service), and launch the `sync.py` script with the `-s` parameter and follow on-screen instructions. You may also specify `--debug` parameter (_must be first_) to show detailed information:

```bash
~$ cd /opt/FIIT-BP-Canaries-Server/
/opt/FIIT-BP-Canaries-Server/$ python3 ./sync.py --debug -s
```

Or import the SQL schemas to your database and create directories for each domain in `/var/mail/vhosts/[DOMAIN.TLD]/`:

[**Virtual domains**](schema/virtual-domains.sql)

[**Virtual users**](schema/virtual-users.sql)

[**Virtual aliases**](schema/virtual-aliases.sql)

If you went the manual route, be sure to reset the permissions by doing:

```bash
~$ sudo chown -R vmail:vmail /var/mail/
```





## Other stuff

- Migration script from MySQL table to Canary Backend [migration.py](migration.py)
- Data migration from Redis to Redis [redis-migrate.py](redis-migrate.py)
