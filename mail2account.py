import sublime
import oauth2mail
import imaplib
import smtplib
from ssl import SSLError
import email
from chardet import detect
from email.header import decode_header
import re
import os
import sys
_PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(_PACKAGE_PATH)
os.chdir(_PACKAGE_PATH)


class SettingHandler:
    def __init__(self, settings):
        self.accounts = {}
        self.settings = settings
        self.mailboxs = self.settings.get("Mailboxs")

    def list_mailbox(self):
        mailbox_list = []
        for mailbox in self.mailboxs:
            mailbox_list.append(mailbox["identity"])
        return mailbox_list

    def add_mailbox(self, identity, name,
                    default='no',
                    smtp_server=None,
                    smtp_port=25,
                    imap_port=25,
                    imap_server=None):
        mailbox = {}
        mailbox["identity"] = identity
        mailbox["parameters"]["name"] = name
        mailbox["parameters"]["smtp_server"] = smtp_server
        mailbox["parameters"]["smtp_port"] = smtp_port
        mailbox["parameters"]["imap_server"] = imap_server
        mailbox["parameters"]["imap_port"] = imap_port
        self.mailboxs.append(mailbox)
        self.settings.set("Mailboxs", self.mailboxs)
        sublime.save_settings(self.setting_file)

    def get_mailbox(self, identity):
        for mailbox in self.mailboxs:
            if mailbox["identity"] == identity:
                return mailbox
        raise NameError("cannot find the relevant mailbox")

    def get_default_identity(self):
        for mailbox in self.mailboxs:
            if "default" in mailbox["parameters"].keys():
                if mailbox["parameters"]["default"] == "yes":
                    return mailbox["identity"]
            else:
                raise NameError("cannot find the default mailbox")


class Account:
    TOKEN_URI = ' '
    AUTH_URI = ' '
    MAIL_SCOPE = ' '
    IMAP_SERVER = ' '
    SMTP_SERVER = ' '
    REDIRECT_URI = ' '
    SSL_IMAP_PORT = SSL_SMTP_PORT = 465
    IMAP_PORT = SMTP_PORT = 25

    def __init__(self, setting_file, identity):
        self.address_book = None
        loaded_settings = sublime.load_settings(setting_file)
        self.setting_container = SettingHandler(loaded_settings)
        self.identity = identity
        self.mailbox = self.setting_container.get_mailbox(self.identity)
        if "client_secret_file" in self.mailbox["parameters"].keys():
            client_secret_json_file = self.mailbox["parameters"]["client_secret_file"]
            client_id = None
            client_secret = None
        else:
            client_secret_json_file = None
            client_id = self.mailbox["parameters"]["client_id"]
            client_secret = self.mailbox["parameters"]["client_secret"]
        self.account = oauth2mail.OauthMailSession(
            client_id=client_id,
            client_secret=client_secret,
            scope=self.MAIL_SCOPE,
            client_secret_json_file=client_secret_json_file,
            auth_uri=self.AUTH_URI,
            token_uri=self.TOKEN_URI,
            redirect_uri=self.REDIRECT_URI)
        if self.account._token_is_cached():
            self.account._load_cached_token()
            if self.account._token_expired():
                self.account._refresh_token()
        else:
            auth_code = self.account._acquire_code()
            self.account._get_token(auth_code)

    def set(self, parameter, value):
        self.mailbox["parameters"][parameter] = value


class GenericSender(Account):
    def __init__(self, setting_file, identity):
        super(GenericSender, self).__init__(setting_file, identity)
        try:
            self.smtp_conn = smtplib.SMTP_SSL(self.SMTP_SERVER,
                                              self.SSL_SMTP_PORT)
        except SSLError:
            self.smtp_conn = smtplib.SMTP(self.SMTP_SERVER, self.SSL_SMTP_PORT)
        self.smtp_conn.ehlo()

    def smtp_authenticate(self):
        authstr = self.account.gen_auth_string(self.identity, True)
        auth_message = self.smtp_conn.docmd("AUTH", "XOAUTH2 " + authstr)
        if auth_message[0] == 235:
            return True
        return False

    def send_mail(self, recipients, msg):
        if isinstance(msg, str):
            self.smtp_conn.sendmail(self.identity, recipients, msg)
        else:
            self.smtp_conn.sendmail(self.identity, recipients, msg.as_string())
        self.smtp_conn.quit()


class GenericReceiver(Account):
    def __init__(self, setting_file, identity):
        super(GenericReceiver, self).__init__(setting_file, identity)
        self.imap_conn = imaplib.IMAP4_SSL(self.IMAP_SERVER)
        if not self.imap_authenticate():
            raise Exception("Cannot pass the authorization.")

    def imap_authenticate(self):
        authstr = self.account.gen_auth_string(self.identity, False)
        auth_message = self.imap_conn.authenticate('XOAUTH2',
                                                   lambda x: authstr)
        if auth_message[0] == 'OK':
            return True
        return False

    def fetch_email(self, email_id=None, location='INBOX'):
        def auto_decode(str_body):
            detected_result = detect(str_body)
            codec = detected_result['encoding']
            return str_body.decode(codec)

        def subject_dealing(raw_subject):
            subject = ''
            decoded_subject = decode_header(raw_subject)
            if decoded_subject[0][1] is None:
                subject = decoded_subject[0][0]
            else:
                subject = decoded_subject[0][0].decode(decoded_subject[0][1])
            subject = subject.replace('\r', '')
            subject = subject.replace('\n', '')
            return subject

        def date_dealing(raw_date_str):
            return raw_date_str[6:26]

        def from_dealing(from_str, flag="name"):
            real_from = ''
            decoded_from = decode_header(from_str)
            tem_str = []
            for i in range(len(decoded_from)):
                if decoded_from[i][1] is None:
                    tem_str.append(decoded_from[i][0])
                else:
                    try:
                        tem_str.append(decoded_from[0][0].decode(decoded_from[0][1]))
                    except:
                        tem_str.append(decoded_from[0][0])
            new_tem_str = []
            for i in tem_str:
                try:
                    new_tem_str.append(i.decode('utf-8'))
                except:
                    new_tem_str.append(i)
            address = ' '.join(new_tem_str)
            if flag == "full":
                return address
            else:
                try:
                    m = re.search(r'^.*(?=(<))', address)
                    real_from = m.group()
                    return real_from
                except:
                    return address
        mail_body = None
        status, last_email_sequence = self.imap_conn.select(location)
        if email_id is None:
            target_email_id = last_email_sequence[0].decode('utf-8', 'ignore')
        else:
            target_email_id = email_id
        msge = {}
        t, raw_msg = self.imap_conn.fetch(target_email_id, 'BODY[]')
        t, header = self.imap_conn.fetch(target_email_id, 'BODY.PEEK[HEADER]')
        msg = email.message_from_string(raw_msg[0][1].decode('utf-8', 'ignore'))
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                mail_body = auto_decode(part.get_payload(decode=True))
                msge["body"] = mail_body.replace('\r', '')
        if "body" not in msge.keys():
            msge["body"] = "Only HTML Version available."
        header_obj = email.message_from_string(header[0][1].decode('utf-8'))
        msge['id'] = target_email_id
        msge["header"] = {}
        for key in ("subject", 'date', 'from', "cc", "bcc", "to"):
            if not isinstance(header_obj[key], str):
                try:
                    msge["header"][key] = header_obj[key].decode('utf-8')
                except:
                    msge["header"][key] = ' '
            else:
                msge['header'][key] = header_obj[key]
        msge["address"] = from_dealing(msge["header"]["from"], "full")
        msge["mailbox"] = from_dealing(msge["header"]["to"], "full")
        for key in ("from", "cc", "bcc", "to"):
            msge["header"][key] = from_dealing(msge["header"][key], "name")
        msge["header"]["subject"] = subject_dealing(msge["header"]["subject"])
        msge["header"]["date"] = date_dealing(msge["header"]["date"])

        return (msge)

    def search_email(self, criteria, location='INBOX'):
        status, email_sequence = self.imap_conn.select(location)
        t, id_sequence = self.imap_conn.search(None, criteria)
        mail_ids = id_sequence[0].decode('utf-8').split(' ')
        return mail_ids

    def fetch_selected_email(self, criteria, location='INBOX'):
        id_sequence = self.search_email(criteria, location)
        msg_list = []
        for mail_id in id_sequence:
            msg_list.append(self.fetch_email(mail_id, location))
        return msg_list


class GoogleAccount(Account):

    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
    MAIL_SCOPE = "https://mail.google.com"
    IMAP_SERVER = "imap.googlemail.com"
    SMTP_SERVER = "smtp.googlemail.com"
    REDIRECT_URI = "http://localhost:10111"

    def __init__(self, setting_file, identity):
        super(GoogleAccount, self).__init__(setting_file, identity)

    def _refresh_token(self):
        self.account._refresh_token()


class GoogleSender(GoogleAccount, GenericSender):
    def __init__(self, setting_file, identity):
        super(GoogleSender, self).__init__(setting_file, identity)


class GoogleReceiver(GoogleAccount, GenericReceiver):
    def __init__(self, setting_file, identity):
        super(GoogleReceiver, self).__init__(setting_file, identity)


class OutlookAccount(Account):
    AUTH_URI = 'https://login.live.com/oauth20_authorize.srf'
    TOKEN_URI = "https://login.live.com/oauth20_token.srf"
    MAIL_SCOPE = "wl.imap wl.offline_access wl.basic"
    IMAP_SERVER = "imap-mail.outlook.com"
    SMTP_SERVER = "smtp-mail.outlook.com"
    REDIRECT_URI = "http://www.mylocalhost.com:10111/"

    def __init__(self, setting_file, identity):
        super(OutlookAccount, self).__init__(setting_file, identity)


class OutlookSender(OutlookAccount, GenericSender):
    SSL_IMAP_PORT = 465
    SSL_SMTP_PORT = 587

    def __init__(self, setting_file, identity):
        super(OutlookSender, self).__init__(setting_file, identity)
        self.smtp_conn.starttls()


class OutlookReceiver(OutlookAccount, GenericReceiver):
    def __init__(self, setting_file, identity):
        super(OutlookReceiver, self).__init__(setting_file, identity)
