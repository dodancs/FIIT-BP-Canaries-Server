import peewee
import datetime
from models.BaseModelMail import BaseModel
from models.VirtualDomain import VirtualDomain


class VirtualAlias(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True,
                             primary_key=True, null=False)
    domain_id = peewee.ForeignKeyField(
        VirtualDomain, backref='aliases', null=False, on_delete='CASCADE')
    source = peewee.CharField(max_length=255, null=False)
    destination = peewee.CharField(max_length=255, null=False)

    class Meta:
        table_name = 'virtual_aliases'
