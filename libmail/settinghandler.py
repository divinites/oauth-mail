import sublime
from imaplib import IMAP4_SSL_PORT


_SETTING_FILE = "OauthMail.sublime-settings"


def load_settings():
    return sublime.load_settings(_SETTING_FILE)


def get_settings():
    settings = SettingHandler()
    settings.initiate()
    return settings


class SettingHandler:
    def __init__(self):
        self.settings = None

    def initiate(self):
        self.settings = load_settings()
        self.mailboxs = self.settings.get("Mailboxs")

    def list_mailbox(self):
        mailbox_list = []
        for mailbox in self.mailboxs:
            mailbox_list.append(mailbox["identity"])
        return mailbox_list

    def is_oauth(self, identity):
        if identity not in self.list_mailbox():
            raise EOFError
        mailbox = self.get_mailbox(identity)
        if "authentication" in mailbox.keys():
            if mailbox["authentication"] == "oauth":
                return True
        return False

    def get_oauth_parameters(self, identity):
        if self.has_secret_file(identity):
            client_secret_json_file = self.get_secret_file(identity)
            return (client_secret_json_file, None, None)
        else:
            client_id = self.get_client_id(identity)
            client_secret = self.get_client_secret(identity)
            return (None, client_id, client_secret)

    def add_mailbox(self,
                    identity,
                    name,
                    default='no',
                    authentication="oauth",
                    smtp_server=None,
                    smtp_port=25,
                    imap_port=25,
                    imap_server=None):
        mailbox = {}
        mailbox["identity"] = identity
        mailbox["parameters"]["name"] = name
        mailbox["authentication"] = authentication
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

    def has_secret_file(self, identity):
        return "client_secret_file" in self.get_mailbox(identity)[
            "parameters"].keys()

    def get_secret_file(self, identity):
        return self.get_mailbox(identity)["parameters"]["client_secret_file"]

    def get_client_id(self, identity):
        return self.get_mailbox(identity)["parameters"]["client_id"]

    def get_client_secret(self, identity):
        return self.get_mailbox(identity)["parameters"]["client_secret"]

    def get_imap(self, identity):
        mailbox = self.get_mailbox(identity)
        if "imap_port" in mailbox["parameters"].keys():
            return (mailbox["parameters"]["imap_server"],
                    int(mailbox["parameters"]["imap_port"]))
        else:
            return (mailbox["parameters"]["imap_server"],
                    IMAP4_SSL_PORT)

    def get_smtp(self, identity):
        mailbox = self.get_mailbox(identity)
        if "smtp_port" in mailbox["parameters"].keys():
            return (mailbox["parameters"]["smtp_server"],
                    int(mailbox["parameters"]["smtp_port"]))
        else:
            return (mailbox["parameters"]["smtp_server"], 0)

    def is_tls(self, identity):
        mailbox = self.get_mailbox(identity)
        if "tls" in mailbox["parameters"].keys():
            if mailbox["parameters"]["tls"] == 'yes':
                return True
        return False

    def get_list_period(self):
        if self.settings.get("List Period"):
            return self.settings.get("List Period")
        else:
            return 7

# class Mailbox:
#     def __init__(self, identity):
#         self.imap_server = None
#         self.imap_port = None
#         self.name = None
#         self.authentication = None
#         self.smtp_server = None
#         self.smtp_port = None
#         self.client_secret_file = None
#         self.client_id = None
#         self.client_secret = None
