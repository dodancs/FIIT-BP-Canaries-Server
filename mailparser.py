import mailbox
from email.header import decode_header
# from bs4 import BeautifulSoup
import email.utils
import datetime
import time


class MailParser:

    def getBody(self, message):
        body = None
        if message.is_multipart():
            for part in message.walk():
                if part.is_multipart():
                    for subpart in part.walk():
                        body = subpart.get_payload(decode=True)
                else:
                    body = part.get_payload(decode=True)
        else:
            body = message.get_payload(decode=True)
        return body

    def getSubject(self, message):
        subject = decode_header(message['Subject'])[0]
        if subject[1]:
            subject = subject[0].decode(subject[1])
        else:
            subject = subject[0]
        return subject

    def getDate(self, message):
        date = datetime.datetime.fromtimestamp(time.mktime(
            email.utils.parsedate(message['Date'])))
        return date

    def getSender(self, message):
        sender = message['From'] if not '<' and not '>' in message['From'] else str(
            message['From']).split('<')[1].split('>')[0]
        return sender

    def getMail(self, maildir):
        if not maildir:
            raise Exception('No maildir specified!')

        dirr = mailbox.Maildir(maildir)
        dirr.lock()

        mails = []

        try:
            for message_id, message in dirr.items():

                if message.get_subdir() != 'new':
                    continue

                mails.append({
                    'date': self.getDate(message),
                    'sender': self.getSender(message),
                    'subject': self.getSubject(message),
                    'body': self.getBody(message),
                })

                message.set_subdir('cur')
                dirr[message_id] = message
        finally:
            dirr.flush()
            dirr.close()

        return mails


# parser = MailParser()

# print(parser.getMail("D:\\Zaloha\\BP - Kanariky\\vhosts\\cloudmail.ga\\Dagmar.Vlckova"))
