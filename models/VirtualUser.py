import peewee
import datetime
from models.BaseModelMail import BaseModel
from models.VirtualDomain import VirtualDomain


class VirtualUser(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    domain_id = peewee.ForeignKeyField(VirtualDomain, backref='aliases')
    password = peewee.CharField(max_length=255)
    email = peewee.CharField(unique=True, max_length=255)

    class Meta:
        table_name = 'virtual_aliases'
