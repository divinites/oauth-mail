from . import oauth2mail
from . import pass2mail
from . import settinghandler
from imaplib import IMAP4_SSL_PORT


class OauthAccount(oauth2mail.OauthMailSession):
    def __init__(self,
                 identity,
                 client_id=None,
                 client_secret=None,
                 scope=None,
                 client_secret_json_file=None,
                 auth_uri=None,
                 token_uri=None,
                 redirect_uri=None):

        self.identity = identity
        self.imap_server = None
        self.imap_port = IMAP4_SSL_PORT
        self.smtp_server = None
        self.smtp_port = 0
        self.tls_flag = False
        super(OauthAccount, self).__init__(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            client_secret_json_file=client_secret_json_file,
            auth_uri=auth_uri,
            token_uri=token_uri,
            redirect_uri=redirect_uri)
        print("OauthMail >>> start initializing OauthAccount Session...")

    def initiate(self):
        if self._token_is_cached():
            self._load_cached_token()
            print("OauthMail >>> Loading cached information...")
            if self._token_expired():
                print("OauthMail >>> Refreshing token...")
                self._refresh_token()
        else:
            print("OauthMail >>> No previous cache, try acquiring...")
            auth_code = self._acquire_code()
            self._get_token(auth_code)
            self._save_in_cache()
            print("OauthMail >>> New token saved.")
        self.set_tls()
        print("OauthMail >>> TLS flag is set to " + str(self.tls_flag))

    def set_tls(self):
        self.tls_flag = settinghandler.get_settings().is_tls(self.identity)


class PassAccount(pass2mail.PassSession):
    def __init__(self, identity):
        super(PassAccount, self).__init__(identity)
        self.imap_server = None
        self.imap_port = IMAP4_SSL_PORT
        self.smtp_server = None
        self.smtp_port = 0
        self.tls_flag = False

    def initiate(self):
        try:
            self.get_imap()
            print("OauthMail >>> IMAP info obtained")
            self.get_smtp()
            print("OauthMail >>> SMTP info obtained")
            self.set_tls()
            print("OauthMail >>> TLS flag is set to " + str(self.tls_flag))
        except:
            print("Error in get necessary parameters")
        if self._is_cached():
            self._load_cache()
            print("OauthMail >>> Loading cached information...")
        else:
            self.get_username()
            print("OauthMail >>> Getting Username/Password")

    def get_imap(self):
        self.imap_server, self.imap_port = settinghandler.get_settings(
        ).get_imap(self.identity)

    def get_smtp(self):
        self.smtp_server, self.smtp_port = settinghandler.get_settings(
        ).get_smtp(self.identity)

    def set_tls(self):
        self.tls_flag = settinghandler.get_settings().is_tls(self.identity)
