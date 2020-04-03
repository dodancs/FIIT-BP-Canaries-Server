import peewee
import datetime
from models.BaseModelCanaries import BaseModel


class Mail(BaseModel):
    id = peewee.BigAutoField(unique=True, index=True, primary_key=True)
    uuid = peewee.CharField(unique=True, index=True, max_length=36)
    canary = peewee.CharField(max_length=36)
    received_on = peewee.DateTimeField()
    mail_from = peewee.CharField(max_length=255, column_name='from')
    subject = peewee.CharField(max_length=255)
    body = peewee.TextField()
    created_at = peewee.DateTimeField(default=datetime.datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'mail'
