import re
from . import mail2account
import smtplib
import imaplib
from .chardet import detect
from email.header import decode_header
from email.parser import HeaderParser
import email
from . import quicklog


def auto_decode(str_body):
    if str_body:
        try:
            detected_result = detect(str_body)
            codec = detected_result['encoding']
            return str_body.decode(codec)
        except LookupError:
            return "Unsupported Codec"
    else:
        return ' '


def subject_dealing(raw_subject):
    subject = ''
    decoded_subject = decode_header(raw_subject)
    if decoded_subject[0][1] is not None:
        subject = decoded_subject[0][0].decode(decoded_subject[0][1])
    else:
        subject = decoded_subject[0][0]
    subject = subject.replace('\r', '')
    subject = subject.replace('\n', '')
    return subject


def date_dealing(raw_date_str):
    return raw_date_str[6:27]


def from_dealing(from_str, flag="name"):
    real_from = ''
    decoded_from = decode_header(from_str)
    tem_str = []
    address = ""
    for i in range(len(decoded_from)):
        if decoded_from[i][1] is None:
            tem_str.append(decoded_from[i][0])
        else:
            try:
                tem_str.append(decoded_from[0][0].decode(decoded_from[
                    0][1]))
            except:
                tem_str.append(decoded_from[0][0])
    new_tem_str = []
    for i in tem_str:
        try:
            new_tem_str.append(i.decode('utf-8'))
        except:
            new_tem_str.append(i)
    try:
        address = ' '.join(new_tem_str)
    except:
        pass
    if flag == "full":
        return address
    else:
        try:
            m = re.search(r'^.*(?=(<))', address)
            real_from = m.group()
            return real_from
        except:
            return address


class Sender:
    def __init__(self):
        self.smtp_conn = None

    def send_mail(self, identity, recipients, msg):
        if isinstance(msg, str):
            quicklog.QuickLog.log("Sending pure Text Message.")
            self.smtp_conn.sendmail(identity, recipients, msg)
        else:
            quicklog.QuickLog.log("Sending pure Text Message.(By Converting)")
            self.smtp_conn.sendmail(identity, recipients, msg.as_string())
        self.smtp_conn.quit()

    def is_smtp_auth(self, auth_message):
        if auth_message[0] == 235:
            quicklog.QuickLog.log("Authentication succeeds.")
            return True
        print(auth_message)
        return False

    def start_smtp(self, smtp_server, smtp_port, tls_flag):
        # try:
        #     self.smtp_conn = smtplib.SMTP_SSL(smtp_server, smtp_port)
        #     quicklog.QuickLog.log("Try establish SSL SMTP connection...")
        # except:
        self.smtp_conn = smtplib.SMTP(smtp_server, smtp_port)
        quicklog.QuickLog.log("Try establish normal SMTP connection...")
        if tls_flag:
            quicklog.QuickLog.log("Starting TLS...")
            self.smtp_conn.starttls()
        self.smtp_conn.ehlo()


class Receiver:
    def __init__(self):
        self.imap_conn = None

    def start_imap(self, imap_server, imap_port, tls_flag):
        try:
            self.imap_conn = imaplib.IMAP4_SSL(imap_server, imap_port)
            quicklog.QuickLog.log("Try establish SSL IMAP connection...")
        except:
            self.imap_conn = imaplib.IMAP4(imap_server, imap_port)
            quicklog.QuickLog.log("Try establish normal SMTP connection...")
            if tls_flag:
                quicklog.QuickLog.log("Starting TLS...")
                self.imap_conn.starttls()

    def is_imap_auth(self, auth_message):
        if auth_message[0] == 'OK':
            quicklog.QuickLog.log("Authentication succeeds.")
            return True
        print(auth_message)
        return False

    def fetch_header(self, email_id, location='INBOX'):
        status, header = self.imap_conn.select(location)
        header = None
        t, header = self.imap_conn.fetch(email_id, '(BODY[HEADER])')
        header_data = header[0][1].decode('utf-8', 'ignore')
        parser = HeaderParser()
        header = parser.parsestr(header_data)
        return header

    def fetch_email(self, email_id=None, location='INBOX'):

        mail_body = None
        status, last_email_sequence = self.imap_conn.select(location)
        if email_id is None:
            target_email_id = last_email_sequence[0].decode('utf-8', 'ignore')
        else:
            target_email_id = email_id
        msge = {}
        t, structure = self.imap_conn.fetch(target_email_id, "BODYSTRUCTURE")
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
        for key in ("subject", 'date', 'from', "cc", "bcc", "to"):
            if not isinstance(header_obj[key], str):
                try:
                    msge[key] = header_obj[key].decode('utf-8')
                except:
                    msge[key] = ' '
            else:
                msge[key] = header_obj[key]
        msge["address"] = from_dealing(msge["from"], "full")
        msge["mailbox"] = from_dealing(msge["to"], "full")
        for key in ("from", "cc", "bcc", "to"):
            msge[key] = from_dealing(msge[key], "name")
        msge["subject"] = subject_dealing(msge["subject"])
        msge["date"] = date_dealing(msge["date"])

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

    def fetch_header_list(self, criteria, location='INBOX'):
        id_sequence = self.search_email(criteria, location)
        header_list = []
        for mail_id in id_sequence:
            header_list.append(self.fetch_header(mail_id, location))
        return id_sequence, header_list


class PassMailBox(mail2account.PassAccount, Sender, Receiver):
    def __init__(self, identity):
        mail2account.PassAccount.__init__(self, identity)
        Sender.__init__(self)
        Receiver.__init__(self)
        quicklog.QuickLog.log("Mailbox initialized.")

    def smtp_authenticate(self):
        auth_message = self.smtp_conn.login(self.username, self.password)
        return self.is_smtp_auth(auth_message)

    def imap_authenticate(self):

        auth_message = self.imap_conn.login(self.username, self.password)
        return self.is_imap_auth(auth_message)


class QuickMailBox(mail2account.OauthAccount, Sender, Receiver):
    def __init__(self,
                 identity,
                 client_id=None,
                 client_secret=None,
                 scope=None,
                 client_secret_json_file=None,
                 auth_uri=None,
                 token_uri=None,
                 redirect_uri=None):
        mail2account.OauthAccount.__init__(
            self,
            identity=identity,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            client_secret_json_file=client_secret_json_file,
            auth_uri=auth_uri,
            token_uri=token_uri,
            redirect_uri=redirect_uri)
        Sender.__init__(self)
        Receiver.__init__(self)
        quicklog.QuickLog.log("Mailbox initialized.")

    def smtp_authenticate(self):
        authstr = self.gen_auth_string(self.identity, True)
        auth_message = self.smtp_conn.docmd("AUTH", "XOAUTH2 " + authstr)
        return self.is_smtp_auth(auth_message)

    def imap_authenticate(self):
        authstr = self.gen_auth_string(self.identity, False)
        auth_message = self.imap_conn.authenticate('XOAUTH2',
                                                   lambda x: authstr)
        return self.is_imap_auth(auth_message)
