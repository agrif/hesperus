import time
import smtplib
from email.mime.text import MIMEText
import re
from textwrap import wrap

from ..plugin import CommandPlugin, PassivePlugin, PollPlugin, PersistentPlugin
from twilio.rest import TwilioRestClient

class SMSAlerter(CommandPlugin, PollPlugin, PersistentPlugin):
    SMS_CHAR_LIMIT = 140
    poll_interval = 15
    persistence_file = 'sms-alerter.json'
    _data = {
        'messages': [],
        'users': {},
    }

    @CommandPlugin.config_types(api_sid=str, api_key=str, wait_period=int,
            grace_period=int, src_number=str, src_email=str, mail_server=str)
    def __init__(self, core, api_sid, api_key, src_number, wait_period=900,
        grace_period=300, src_email='hesperus@localhost', mail_server='localhost:25'):
        super(SMSAlerter, self).__init__(core)
        self.api = TwilioRestClient(api_sid, api_key)
        self.wait_period = wait_period
        self.grace_period = grace_period
        self.src_number = src_number
        self.src_email = src_email
        self.mail_server = mail_server.split(':')
        self.load_data()

    def remove_user(self, name):
        if name in self._data['users']:
            del self._data['users'][name]
            self.save_data()

    def add_user(self, name, sms_contact=None, email_contact=None):
        now = int(time.time())
        if name not in self._data['users']:
            self._data['users'][name] = {
                'enabled': True,
                'sms_contact': sms_contact,
                'email_contact': email_contact,
                'last_active': now,
            }
        else:
            if sms_contact is not None:
                self._data['users'][name]['sms_contact'] = sms_contact
                self.log_debug('Enabled SMS alerts for ' + name)
            if email_contact is not None:
                self._data['users'][name]['email_contact'] = email_contact
                self.log_debug('Enabled email alerts for ' + name)
        self.save_data()

    update_user = add_user

    def add_message(self, **kwargs):
        self._data['messages'].append(kwargs)
        self.save_data()
        self.log_debug('Added message to queue: {msg}'.format(msg=kwargs))

    def update_last_active(self, name):
        self._data['users'][name]['last_active'] = int(time.time())
        #remove queued messages
        self._data['messages'] = [msg for msg in self._data['messages'] \
            if msg['dest'] != name]
        self.save_data()

    @CommandPlugin.register_command(r'emailalert(?:\s+(.+))?')
    def email_alert_command(self, chans, name, match, direct, reply):
        if match.group(1):
            if re.match(r'^.+@.+$', match.group(1)):
                email_addr = match.group(1)
                if name in self._data['users']:
                    self.update_user(name, email_contact=email_addr)
                    reply('I\'ve updated your email alert address')
                else:
                    self.add_user(name, email_contact=email_addr)
                    reply('Ok, I\'ll send you an alert if someone pings you')
        else:
            if name in self._data['users']:
                self.remove_user(name)
                reply('Sorry, I\'ll stop bugging you then')
            else:
                reply('You need to give me a way to contact you if you want alerts')

    @CommandPlugin.register_command(r'smsalert(?:\s+(.+))?')
    def sms_alert_command(self, chans, name, match, direct, reply):
        if match.group(1):
            if re.match(r'^(\+\d{10,}|\d{10})$', match.group(1)):
                sms_number = match.group(1)
                if name in self._data['users']:
                    self.update_user(name, sms_contact=sms_number)
                    reply('I\'ve updated your SMS alert address')
                else:
                    self.add_user(name, sms_contact=sms_number)
                    reply('Ok, I\'ll send you an alert if someone pings you')
            else:
                reply('I don\'t know what to do with that, I need a 10+ digit phone number')
        else:
            if name in self._data['users']:
                self.remove_user(name)
                reply('Sorry, I\'ll stop bugging you then')
            else:
                reply('You need to give me a way to contact you if you want alerts')

    @PassivePlugin.register_pattern(r'([\S]+)[:,]\s+(.+)')
    def ping_message(self, chans, name, match, direct, reply):
        target = match.group(1)
        target_msg = match.group(2).strip()
        now = int(time.time())
        if target in self._data['users']:
            if self._data['users'][target]['enabled'] and \
                    now - self._data['users'][target]['last_active'] > self.wait_period:
                self.add_message(src=name, dest=target, msg=target_msg, ts=now)

    @PassivePlugin.register_pattern(r'^')
    def activity_watch(self, chans, name, match, direct, reply):
        if name in self._data['users']:
            self.update_last_active(name)

    def poll(self):
        #if no reply to dm after grace_period, do notify
        now = int(time.time())
        to_send = [msg for msg in self._data['messages'] \
            if now - msg['ts'] > self.grace_period]
        if to_send:
            self.log_debug('Found {c} messages to send in queue'.format(
                c=len(to_send)))
            for msg in to_send:
                self.send_message(msg)
                self._data['messages'].remove(msg)
                self.update_last_active(msg['dest'])
            self.save_data()
        yield

    def send_message(self, message):
        user = self._data['users'][message['dest']]
        body = '{msg[src]} said: {msg[msg]}'.format(msg=message)
        if user['sms_contact']:
            self._send_sms(user['sms_contact'], body)
        if user['email_contact']:
            self._send_email(user['email_contact'], body)

    def _send_sms(self, dest, body):
        try:
            self.api.sms.messages.create(
                from_=self.src_number, to=dest, body=body[:self.SMS_CHAR_LIMIT])
        except Exception as err:
            self.log_warning(err)
        else:
            self.log_debug('Sent SMS to: ' + dest)

    def _send_email(self, dest, body):
        envlp = MIMEText(body)
        envlp['Subject'] = 'IRCAlert'
        envlp['From'] = self.src_email
        envlp['To'] = dest
        try:
            conn = smtplib.SMTP(*self.mail_server)
            conn.sendmail(envelope['From'], [envelope['To'],], envelope.as_string())
            conn.quit()
        except Exception as err:
            self.log_warning(err)
        else:
            self.log_debug('Sent email to: ' + dest)
