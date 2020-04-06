import peewee
import datetime
from models.BaseModelMail import BaseModel
from models.VirtualDomain import VirtualDomain


class VirtualUser(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True,
                             primary_key=True, null=False)
    domain_id = peewee.ForeignKeyField(
        VirtualDomain, backref='aliases', null=False, on_delete='CASCADE')
    password = peewee.CharField(max_length=255, null=False)
    email = peewee.CharField(unique=True, max_length=255, null=False)

    class Meta:
        table_name = 'virtual_aliases'
