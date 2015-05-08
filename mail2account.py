import sublime
import oauth2code
import imaplib
import smtplib
from ssl import SSLError


class SettingHandler:
    def __init__(self, setting_file):
        self.accounts = {}
        self.settings = sublime.load_settings(setting_file)
        self.mailboxs = self.settings.get("Mailboxs")
        self.setting_file = setting_file

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
    REDIRECT_URI = "localhost:10111"
    SSL_IMAP_PORT = SSL_SMTP_PORT = 465
    IMAP_PORT = SMTP_PORT = 25

    def __init__(self, setting_file, identity):
        self.address_book = None
        self.setting_container = SettingHandler(setting_file)
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

        self.account = oauth2code.OAuth2(client_secret_json_file, client_id,
                                         client_secret, self.MAIL_SCOPE,
                                         self.AUTH_URI, self.TOKEN_URI,
                                         self.REDIRECT_URI)

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

    def imap_authenticate(self):
        authstr = self.account.gen_auth_string(self.identity, False)
        self.imap_conn.authenticate('XOAUTH2', lambda x: authstr)


class GoogleAccount(Account):

    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
    MAIL_SCOPE = "https://mail.google.com"
    IMAP_SERVER = "imap.googlemail.com"
    SMTP_SERVER = "smtp.googlemail.com"

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
