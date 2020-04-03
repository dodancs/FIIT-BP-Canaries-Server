import peewee
import json

# Open configuration file
with open('config.json', encoding='utf8') as config_file:
    Config = json.load(config_file)

db = peewee.MySQLDatabase(
    Config['mail']['db_db'], host=Config['mail']['db_host'], port=Config['mail']['db_port'], user=Config['mail']['db_user'], passwd=Config['mail']['db_password'], charset=Config['mail']['db_charset'])


class BaseModel(peewee.Model):
    class Meta:
        database = db
