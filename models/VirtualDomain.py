import peewee
import datetime
from models.BaseModelMail import BaseModel


class VirtualDomain(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    name = peewee.CharField(max_length=255)

    class Meta:
        table_name = 'virtual_domains'
