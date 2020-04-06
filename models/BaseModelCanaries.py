import peewee
import json

# Open configuration file
try:
    with open('config.json', encoding='utf8') as config_file:
        Config = json.load(config_file)
except:
    print('Unable to open config.json!')
    print('If you haven\'t created a configuration file, please use the example configuration file as a guide.')
    print('Otherwise, make sure the file permissions are set correctly.')
    exit(1)

db = peewee.MySQLDatabase(
    Config['canary']['db_db'], host=Config['canary']['db_host'], port=Config['canary']['db_port'], user=Config['canary']['db_user'], passwd=Config['canary']['db_password'], charset=Config['canary']['db_charset'])


class BaseModel(peewee.Model):
    class Meta:
        database = db
