import time
import smtplib
from email.mime.text import MIMEText
import re

from ..plugin import CommandPlugin, PassivePlugin, PollPlugin
from data247.api import ApiConnection

class SMSAlerter(CommandPlugin, PollPlugin):
    poll_interval = 15

    @CommandPlugin.config_types(api_user=str, api_pass=str, wait_period=int, grace_period=int, mail_server=str, src_email=str)
    def __init__(self, core, api_user, api_pass, wait_period=900, grace_period=300,
                mail_server='localhost:25', src_email='hesperus@localhost'):
        super(SMSAlerter, self).__init__(core)
        self._data = {
            'messages': [],
            'users': {},
            'contacts': {},
        }
        self.api = ApiConnection(api_user, api_pass)
        self.wait_period = wait_period
        self.grace_period = grace_period
        self.mail_server = mail_server.split(':')
        self.src_email = src_email

    @CommandPlugin.register_command(r'smsalert\s+(.+)')
    def alert_command(self, chans, name, match, direct, reply):
        if re.match(r'^(?:\S+@(?:[\w\d-]+\.)*[\w\d-]+|\d+)$', match.group(1)):
            if name in self._data['users']:
                del self._data['users'][name]
                reply('Fine, I won\'t send you alerts anymore')
            else:
                if re.match(r'^\d+$', match.group(1)):
                    contact = self.api.get_number_info([match.group(1)]).phones[0].sms_address
                else:
                    contact = match.group(1)
                self.log_debug('Using {contact} as contact for {user}'.format(contact=contact, user=name))
                self._data['users'][name] = {
                    'enabled': True,
                    'contact': contact,
                    'last_active': int(time.time()),
                }
                reply('Ok, you\'re on THE LIST now')
        else:
            reply('I don\'t know what to do with that, give me a cell phone number or an email address')

    @PassivePlugin.register_pattern(r'([\w\d]+)[:,]\s+(.+)')
    def ping_message(self, chans, name, match, direct, reply):
        target = match.group(1)
        target_msg = match.group(2)
        now = int(time.time())
        if target in self._data['users']:
            if self._data['users'][target]['enabled'] and \
                    now - self._data['users'][target]['last_active'] > self.wait_period:
                self._data['messages'].append({
                    'src': name,
                    'dest': target,
                    'msg': target_msg,
                    'ts': now,
                })

    @PassivePlugin.register_pattern(r'')
    def activity_watch(self, chans, name, match, direct, reply):
        if name in self._data['users']:
            self._data['users'][name]['last_active'] = int(time.time())
        self._data['messages'] = [msg for msg in self._data['messages'] \
            if msg['target'] != name]

    def poll(self):
        #if no reply to dm after 5m, do notify
        now = int(time.time())
        to_send = [msg for msg in self._data['messages'] \
            if now - msg['ts'] > self.grace_period]
        for msg in to_send:
            self.notify(msg['src'], msg['dest'], msg['msg'])
            self._data['messages'].remove(msg)
            self.log_debug('Sent notification to {msg[dest]} ({contact}) from {msg[src]}'.format(
                msg=msg,
                contact=self._data['users'][msg['dest']]))
        yield

    def notify(self, src, dest, msg):
        msg = MIMEText('{src} sent: {msg}'.format(src=src, msg=msg))
        msg['Subject'] = 'IRCAlert for {dest}'.format(dest=dest)
        msg['From'] = self.src_email
        msg['To'] = self._data['users'][dest]['contact']

        s = smtplib.SMTP(*self.mail_server)
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()
