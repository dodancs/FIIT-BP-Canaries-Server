import peewee
import datetime
from models.BaseModelMail import BaseModel
from models.VirtualDomain import VirtualDomain


class VirtualAlias(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    domain_id = peewee.ForeignKeyField(VirtualDomain, backref='aliases')
    source = peewee.CharField(max_length=255)
    destination = peewee.CharField(max_length=255)

    class Meta:
        table_name = 'virtual_aliases'
