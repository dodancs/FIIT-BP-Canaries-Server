import peewee
import datetime
from models.BaseModelCanaries import BaseModel


class Domain(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    uuid = peewee.CharField(unique=True, index=True, max_length=36)
    domain = peewee.CharField(max_length=255)
    created_at = peewee.DateTimeField()
    updated_at = peewee.DateTimeField()

    class Meta:
        table_name = 'domains'
