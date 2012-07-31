import time
import smtplib
from email.mime.text import MIMEText
import re
from textwrap import wrap

from ..plugin import CommandPlugin, PassivePlugin, PollPlugin, PersistentPlugin
from data247.api import ApiConnection

class SMSAlerter(CommandPlugin, PollPlugin, PersistentPlugin):
    poll_interval = 15
    persistence_file = 'sms-alerter.json'
    _data = {
        'messages': [],
        'users': {},
        'contacts': {},
    }

    @CommandPlugin.config_types(api_user=str, api_pass=str, wait_period=int, grace_period=int, mail_server=str, src_email=str)
    def __init__(self, core, api_user, api_pass, wait_period=900, grace_period=300,
                mail_server='localhost:25', src_email='hesperus@localhost'):
        super(SMSAlerter, self).__init__(core)
        self.api = ApiConnection(api_user, api_pass)
        self.wait_period = wait_period
        self.grace_period = grace_period
        self.mail_server = mail_server.split(':')
        self.src_email = src_email
        self.load_data()

    def verify_contact(self, contact):
        if re.match(r'^\d{10}$', contact):
            if contact not in self._data['contacts']:
                self._data['contacts'][contact] = \
                    self.api.get_number_info([contact]).phones[0].sms_address
                self.save_data()
            self.log_debug('Using {sms_addr} for {contact}'.format(
                sms_addr=self._data['contacts'][contact],
                contact=contact))
            return self._data['contacts'][contact]
        elif re.match(r'^\S+@(?:[\w\d-]+\.)*[\w\d-]+$', contact):
            return contact
        else:
            return None

    def remove_user(self, name):
        if name in self._data['users']:
            del self._data['users'][name]
            self.save_data()

    def add_user(self, name, contact):
        now = int(time.time())
        self._data['users'][name] = {
            'enabled': True,
            'contact': contact,
            'last_active': now,
        }
        self.save_data()
        self.log_debug('Enabled alerts for {name} -> {contact}'.format(
            name=name,
            contact=contact))

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

    @CommandPlugin.register_command(r'smsalert(?:\s+(.+))?')
    def alert_command(self, chans, name, match, direct, reply):
        if match.group(1):
            contact = self.verify_contact(match.group(1))
            if not contact:
                reply('I don\'t know what to do with that, I need a 10 digit number or an email address')
            elif name in self._data['users']:
                self.update_user(name, contact)
                reply('I\'ve updated your alert address')
            else:
                self.add_user(name, contact)
                reply('Ok, I\'ll send you an alert if someone pings you')
        else:
            if name in self._data['users']:
                self.remove_user(name)
                reply('Sorry, I\'ll stop bugging you then')
            else:
                reply('You need to give me a way to contact you if you want alerts')

    @PassivePlugin.register_pattern(r'([\w\d]+)[:,]\s+(.+)')
    def ping_message(self, chans, name, match, direct, reply):
        target = match.group(1)
        target_msg = match.group(2).strip()
        if len(target_msg) > 100:
            target_msg = wrap(target_msg, 100)[0].strip() + '...'
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
        envlp = MIMEText('{msg[src]} said: {msg[msg]}'.format(msg=message))
        envlp['Subject'] = 'IRCAlert for {msg[dest]}'.format(msg=message)
        envlp['From'] = self.src_email
        envlp['To'] = self._data['users'][message['dest']]['contact']
        self._send_email(envlp)
        self.log_debug('Sent alert from {msg[src]} to {msg[dest]}'.format(
            msg=message))

    def _send_email(self, envelope):
        conn = smtplib.SMTP(*self.mail_server)
        conn.sendmail(envelope['From'], [envelope['To']], envelope.as_string())
        conn.quit()
