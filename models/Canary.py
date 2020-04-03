import peewee
import datetime
from models.BaseModelCanaries import BaseModel


class Canary(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    uuid = peewee.CharField(unique=True, index=True, max_length=36)
    domain = peewee.CharField(max_length=36)
    site = peewee.CharField(max_length=36)
    assignee = peewee.CharField(max_length=36)
    updated_by = peewee.CharField(max_length=36)
    testing = peewee.BooleanField()
    setup = peewee.BooleanField()
    email = peewee.CharField(max_length=255)
    password = peewee.CharField(max_length=255)
    data = peewee.TextField()
    created_at = peewee.DateTimeField()
    updated_at = peewee.DateTimeField()

    class Meta:
        table_name = 'canaries'
