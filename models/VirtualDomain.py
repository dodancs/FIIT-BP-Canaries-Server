import peewee
import datetime
from models.BaseModelMail import BaseModel


class VirtualDomain(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True,
                             primary_key=True, null=False)
    name = peewee.CharField(max_length=255, null=False, unique=True)

    class Meta:
        table_name = 'virtual_domains'
