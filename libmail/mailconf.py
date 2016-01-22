from . import mailbox
from . import settinghandler
from . import quicklog
G_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
G_TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
G_MAIL_SCOPE = "https://mail.google.com"
G_REDIRECT_URI = "http://localhost:10111"
M_AUTH_URI = 'https://login.live.com/oauth20_authorize.srf'
M_TOKEN_URI = "https://login.live.com/oauth20_token.srf"
M_MAIL_SCOPE = "wl.imap wl.offline_access wl.basic"
M_REDIRECT_URI = "http://www.mylocalhost.com:10111/"


def google_account(identity):
    oauth_paras = settinghandler.get_settings().get_oauth_parameters(identity)
    client_secret_json_file = oauth_paras[0]
    client_id = oauth_paras[1]
    client_secret = oauth_paras[2]
    if client_secret_json_file or (client_id and client_secret):
        quicklog.QuickLog.log("Successfully get client_file/client_secret.")

    google_oauth_mailbox = mailbox.OauthMailBox(
        identity=identity,
        client_id=client_id,
        client_secret=client_secret,
        scope=G_MAIL_SCOPE,
        client_secret_json_file=client_secret_json_file,
        auth_uri=G_AUTH_URI,
        token_uri=G_TOKEN_URI,
        redirect_uri=G_REDIRECT_URI)
    google_oauth_mailbox.imap_server = "imap.googlemail.com"
    google_oauth_mailbox.smtp_server = "smtp.googlemail.com"
    google_oauth_mailbox.initiate()
    quicklog.QuickLog.log("Google Account initiated.")
    return google_oauth_mailbox


def outlook_account(identity):
    oauth_paras = settinghandler.get_settings().get_oauth_parameters(identity)
    client_secret_json_file = oauth_paras[0]
    client_id = oauth_paras[1]
    client_secret = oauth_paras[2]
    if client_secret_json_file or (client_id and client_secret):
        quicklog.QuickLog.log("Successfully get client_file/client_secret.")
    outlook_oauth_mailbox = mailbox.OauthMailBox(
        identity=identity,
        client_id=client_id,
        client_secret=client_secret,
        scope=M_MAIL_SCOPE,
        client_secret_json_file=client_secret_json_file,
        auth_uri=M_AUTH_URI,
        token_uri=M_TOKEN_URI,
        redirect_uri=M_REDIRECT_URI)
    outlook_oauth_mailbox.imap_server = "imap-mail.outlook.com"
    outlook_oauth_mailbox.smtp_server = "smtp-mail.outlook.com"
    outlook_oauth_mailbox.imap_port = 465
    outlook_oauth_mailbox.smtp_port = 587
    outlook_oauth_mailbox.initiate()
    quicklog.QuickLog.log("Outlook Account initiated.")
    return outlook_oauth_mailbox


def pass_account(identity):
    pass_mailbox = mailbox.PassMailBox(identity)
    pass_mailbox.initiate()
    quicklog.QuickLog.log("Pass Account initiated.")
    return pass_mailbox
