import time
import imaplib
import email
import re

from ..plugin import PollPlugin

class ImapWatcher(PollPlugin):
    poll_interval = 30

    @PollPlugin.config_types(username=str, password=str, use_ssl=bool, \
            mail_host=str, mail_port=int, subject_pattern=str, message_pattern=str)
    def __init__(self, core, username, password, mail_host, subject_pattern, \
            message_pattern, mail_port=None, use_ssl=True):
        super(ImapWatcher, self).__init__(core)

        if mail_port is None:
            mail_port = 993 if use_ssl else 143
        self._conn_data = {
            'class': imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4,
            'host': mail_host,
            'port': mail_port,
            'username': username,
            'password': password,
        }
        self._subject_pattern = re.compile(subject_pattern)
        self._message_pattern = re.compile(message_pattern)

    def poll(self):
        for msg in self._filter_messages(self._get_new_messages()):
            self.log_debug('Found a new message: ' + msg[0])
            self._notify(*msg)
        yield

    def _filter_messages(self, messages):
        return ((msg.get('Subject', ''), self._get_msg_text(msg)) for msg in messages \
            if self._subject_pattern.search(msg.get('Subject', '')) and \
                self._message_pattern.search(self._get_msg_text(msg)))

    def _get_msg_text(self, message):
        return '\n'.join(p.get_payload().strip() for p in message.walk() \
            if p.get_content_subtype() == 'plain').strip()

    def _notify(self, subject, content):
        message = 'New Message: {subject} :: {text}'.format(
            subject=subject,
            text='|'.join(l for l in content.replace('\r\n', '\n').split('\n') if l))
        for chan in self.channels:
            self.parent.send_outgoing(chan, message)

    def _get_new_messages(self):
        try:
            conn = self._get_conn()
        except Exception:
            return []
        (_, (new_message_ids,)) = conn.search(None, '(UNSEEN)')
        if not new_message_ids:
            new_messages = []
        else:
            new_messages = [email.message_from_string(conn.fetch(mid, '(RFC822)')[1][0][1]) \
                for mid in new_message_ids.split(' ')]
        conn.logout()
        self.log_debug('Found %d new messages' % len(new_messages))
        return new_messages

    def _get_conn(self):
        conn = self._conn_data['class'](self._conn_data['host'],
            self._conn_data['port'])
        conn.login(self._conn_data['username'], self._conn_data['password'])
        conn.select('INBOX')
        return conn
