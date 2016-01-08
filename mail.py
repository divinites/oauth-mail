import os
from .libmail import mailconf
from .libmail import settinghandler
# from .libmail import pass2mail
import sublime_plugin
import threading
import sublime
import re
import queue
from datetime import date
from datetime import timedelta
from time import sleep

# Set YAML flags and global variable _LOADED_SETTINGS

_LOADED_SETTINGS = None
_SETTING_FILE = "OauthMail.sublime-settings"
_SENDER_FLAG = 'meta.address.sender string'
_ATTACHMENT_FLAG = 'meta.attachment string'
_SUBJECT_FLAG = 'meta.subject string'
_MAIL_PREFIX_FLAG = 'text.email '
_MESSAGE_FLAG = 'meta.message'


def _RECIPIENTS_FLAG(typ):
    """
    Since there are at least three types of recipients flags :CC BCC and To
    so, define a function here instead of three constants.
    """
    return 'meta.address.recipient.{0} string'.format(typ)


_MAIL_SYNTAX_PATH = "Packages/{}/mail.tmLanguage".format(__package__)
_LIST_SYNTAX_PATH = "Packages/{}/list.tmLanguage".format(__package__)
_LIST_THEME_PATH = "Packages/{}/list.tmTheme".format(__package__)
_MAIL_LIST_SYNTAX_PATH = ' '
_SUCCESS_MESSAGE = "Message Successfully Sent."
_FAIL_MESSAGE = "Message failed."
_MAIL_CLASS_DICT = {
    "gmail": mailconf.google_account,
    "outlook": mailconf.outlook_account,
    "generic": mailconf.pass_account
}


def plugin_loaded():
    global _LOADED_SETTINGS
    _LOADED_SETTINGS = sublime.load_settings(_SETTING_FILE)


def check_mailbox_type(identity):
    """
    Check mailbox types.
    """
    checker_dict = {
        "outlook": "^[a-z0-9](\.?[a-z0-9]){5,}@(live|outlook|hotmail)\..+",
        "gmail": "^[a-z0-9](\.?[a-z0-9]){5,}@g(oogle)?mail\.com"
    }
    for name, checker in checker_dict.items():
        prog = re.compile(checker)
        result = prog.match(identity)
        if result:
            print("OauthMail >>> " + name + " Mailbox detected")
            return name
    print("OauthMail >>>  Not an OauthMail, will need Username/Password.")
    return "generic"


class MailWriteCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    def run(self,
            From="",
            To="",
            Cc="",
            Bcc="",
            Subject="",
            Body="",
            Signature=None,
            Attachments=[]):
        _SETTINGS = settinghandler.get_settings()
        view = self.window.new_file()
        view.set_syntax_file(_MAIL_SYNTAX_PATH)
        snippet = ""
        snippet += "From   : ${1:%s}\n" % _SETTINGS.get_default_identity()
        snippet += "To     : ${2:%s}\n" % To
        snippet += "Cc     : ${3:%s}\n" % Cc
        snippet += "Bcc    : ${4:%s}\n" % Bcc
        snippet += "Attach :\n"
        if Attachments:
            for a in Attachments:
                snippet += "    - %s\n" % a
        snippet += "Subject: ${5:%s}\n" % Subject
        snippet += "\n"

        snippet += "${6:%s}\n" % Body

        view.run_command("insert_snippet", {"contents": snippet})


class SendMailThread(threading.Thread):
    def __init__(self, msg, identity, recipients):
        threading.Thread.__init__(self)
        self.msg = msg
        self.recipients = recipients
        self.identity = identity

    def run(self):

        mail_type = check_mailbox_type(self.identity)
        account = _MAIL_CLASS_DICT[mail_type](self.identity)

        print("OauthMail >>> " + self.identity + " Account object realized.")
        account.start_smtp(account.smtp_server, account.smtp_port,
                           account.tls_flag)
        print("OauthMail >>> Successfully connect SMTP server, ready to sent!")
        sleep(10)
        if account.smtp_authenticate():
            print("OauthMail >>> Start Sending email...")
            account.send_mail(self.identity, self.recipients, self.msg)
            print("OauthMail >>> Succeeded.")
            sublime.status_message(_SUCCESS_MESSAGE)
        else:
            print("OauthMail >>> failed.")
            sublime.status_message(_FAIL_MESSAGE)

#        self.server_account.authenticate(0)
#        try:
#            self.server_account.send_mail(self.recipients,
#                                          self.msg.as_string())
#        except Exception as e:
#            sublime.error_message("Sending failed: %s" % e)


class MailSendCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        view = self.window.active_view()
        if not view:
            return False
        regions = view.find_by_selector(_MAIL_PREFIX_FLAG)
        if not regions:
            return False
        return True

    def run(self):
        self.window.run_command("show_panel",
                                {"panel": "console",
                                 "toggle": "true"})
        _SETTINGS = settinghandler.get_settings()
        view = self.window.active_view()

        def get_text(selector, joiner=" "):
            regions = view.find_by_selector(_MAIL_PREFIX_FLAG + selector)
            result = joiner.join([view.substr(r) for r in regions])
            return result

        # get identity
        if _SETTINGS.show_prompt():
            view.run_command("show_panel", {"panel": "output.exec"})
        identity = get_text(_SENDER_FLAG).strip()

        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        message = get_text(_MESSAGE_FLAG)
        if message.startswith('#!'):
            message = message.split("\n", 1)[1]

        # compose message
        content = MIMEText(message, "plain")

        attachments = []
        for r in view.find_by_selector(_ATTACHMENT_FLAG):
            attachment = view.substr(r)
            if not os.path.exists(attachment):
                sublime.error_message("Attachment does not exist: %s" %
                                      attachment)
                return
            attachments.append(attachment)

        message_info = MIMEMultipart()
        message_info['Subject'] = get_text(_SUBJECT_FLAG)
        message_info.attach(content)
        if attachments:
            import mimetypes
            from email import encoders
            from email.mime.audio import MIMEAudio
            from email.mime.base import MIMEBase
            from email.mime.image import MIMEImage
            from email.mime.text import MIMEText
            for path in attachments:

                # code taken from http://docs.python.org/2/
                # library/email-examples.html
                #
                # Guess the content type based on the file's extension.
                # Encodingwill be ignored, although we should check for
                # simple things like
                # gzip'd or compressed files.
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded
                    # (compressed), so
                    # use a generic bag-of-bits type.
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                if maintype == 'text':
                    fp = open(path)
                    # Note: we should handle calculating the charset
                    msg = MIMEText(fp.read(), _subtype=subtype)
                    fp.close()
                elif maintype == 'image':
                    fp = open(path, 'rb')
                    msg = MIMEImage(fp.read(), _subtype=subtype)
                    fp.close()
                elif maintype == 'audio':
                    fp = open(path, 'rb')
                    msg = MIMEAudio(fp.read(), _subtype=subtype)
                    fp.close()
                else:
                    fp = open(path, 'rb')
                    msg = MIMEBase(maintype, subtype)
                    msg.set_payload(fp.read())
                    fp.close()
                    # Encode the payload using Base64
                    encoders.encode_base64(msg)
                # Set the filename parameter
                filename = os.path.basename(path)
                msg.add_header('Content-Disposition',
                               'attachment',
                               filename=filename)
                message_info.attach(msg)
        recipients = []
        for typ in ('to', 'cc', 'bcc'):
            rcpt = get_text(_RECIPIENTS_FLAG(typ), joiner=", ")
            if not rcpt:
                continue
            recipients += [x for x in re.split(r",\s*", str(rcpt))]

            if typ == 'bcc':
                continue
            message_info[typ.capitalize()] = rcpt
            print("OauthMail >>> Message prepared.")
            mail_thread = SendMailThread(message_info, identity, recipients)
            mail_thread.start()
            # self.window.run_command("hide_panel",
            #                         {"cancel": "true"})


class AttachThisFileCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        view = self.window.active_view()
        if not view:
            return False
        regions = view.find_by_selector(_MAIL_PREFIX_FLAG)
        if not regions:
            return False
        return True

    def run(self):
        view = self.window.active_view()
        if not view:
            return

        if not view.file_name():
            sublime.error_message("This view has no associated filename.")
            return

        self.window.run_command('email_write', {'Attachments':
                                                [view.file_name()]})


class SendAsMailCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()

        selected = ""

        for r in view.sel():
            selected += view.substr(r)
            if selected and not selected.endswith("\n"):
                selected += "\n"

        if not selected:
            selected = view.substr(sublime.Region(0, view.size()))

        split_line = "-" * 20 + "\n"

        self.window.run_command('mail_write', {'Body': split_line + selected})


class ShowMailCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    def on_done(self, mail_id):
        _SETTINGS = settinghandler.get_settings()
        view = self.window.new_file()
        view.set_syntax_file(_MAIL_SYNTAX_PATH)
        identity = _SETTINGS.get_default_identity()
        mailbox_queue = queue.Queue()
        mail_queue = queue.Queue()
        IMAP_thread = MailBoxConnectionThread(mailbox_queue, identity)
        print("OauthMail >>> IMAP thread establsihed.")
        IMAP_thread.start()
        fetch_mail = FetchMailThread(mail_id, mailbox_queue, mail_queue)
        print("OauthMail >>> Fetching mails...")
        fetch_mail.start()
        print_in_view = PrintMailInView(mail_queue, view)
        print_in_view.start()

    def run(self):
        sublime.active_window().run_command('hide_panel')
        sublime.active_window().show_input_panel('Mail ID:', '', self.on_done,
                                                 None, None)


class ListRecentMailCommand(sublime_plugin.WindowCommand):
    def is_enable(self):
        return True

    def run(self):
        _SETTINGS = settinghandler.get_settings()
        list_period = _SETTINGS.get_list_period()
        since_date = date.today() - timedelta(days=list_period)
        date_string = "(SINCE \"" + since_date.strftime("%d-%b-%Y") + "\")"
        view = self.window.new_file()
        identity = _SETTINGS.get_default_identity()
        mailbox_queue = queue.Queue()
        list_queue = queue.Queue()
        IMAP_thread = MailBoxConnectionThread(mailbox_queue, identity)
        IMAP_thread.start()
        self.window.run_command("show_panel",
                                {"panel": "console",
                                 "toggle": "true"})
        print("OauthMail >>> IMAP thread established.")
        list_mail = GetEmailListThread(mailbox_queue, list_queue, date_string,
                                       None)
        list_mail.start()
        print_in_view = PrintListInView(list_queue, view)
        print_in_view.start()


class MailBoxConnectionThread(threading.Thread):
    def __init__(self, out_mailbox_queue, identity):
        threading.Thread.__init__(self)
        self.mailbox_queue = out_mailbox_queue
        self.mailbox = _MAIL_CLASS_DICT[check_mailbox_type(identity)](identity)

    def run(self):
        self.mailbox.start_imap(self.mailbox.imap_server,
                                self.mailbox.imap_port, self.mailbox.tls_flag)
        if self.mailbox.imap_authenticate():
            self.mailbox_queue.put(self.mailbox)


class GetEmailListThread(threading.Thread):
    def __init__(self,
                 in_mailbox_queue,
                 out_list_queue,
                 date_string,
                 location=None):
        threading.Thread.__init__(self)
        self.mailbox_queue = in_mailbox_queue
        self.list_queue = out_list_queue
        self.date_string = date_string
        if location is None:
            self.location = 'INBOX'
        else:
            self.location = location

    def run(self):
        mailbox = self.mailbox_queue.get()
        mail_list = mailbox.fetch_header_list(self.date_string)
        print("OauthMail >>> Fetching mail headers...")
        self.list_queue.put(mail_list)
        self.mailbox_queue.put(mailbox)


class FetchMailThread(threading.Thread):
    def __init__(self,
                 email_id=None,
                 in_mailbox_queue=None,
                 out_mail_queue=None,
                 location=None):
        threading.Thread.__init__(self)
        self.email_id = email_id
        self.mailbox_queue = in_mailbox_queue
        self.mail_queue = out_mail_queue
        self.body = None
        if location is None:
            self.location = 'INBOX'

    def run(self):
        mailbox = self.mailbox_queue.get()
        msg = mailbox.fetch_email(self.email_id, self.location)
        print("OauthMail >>> Mail Fetched.")
        self.mail_queue.put(msg)
        self.mailbox_queue.put(mailbox)


class PrintListInView(threading.Thread):
    def __init__(self, list_queue, view):
        super(PrintListInView, self).__init__(self)
        self.list_queue = list_queue
        self.view = view

    def run(self):
        def split_line(subject):
            subject_words = subject.split()
            first_line = ''
            second_line = ''
            for word in subject_words:
                if len(first_line) < 30:
                    first_line += ' ' + word
                else:
                    second_line += " " + word
            return first_line, second_line

        self.view.set_syntax_file(_LIST_SYNTAX_PATH)
        self.view.settings().set('color_scheme', _LIST_THEME_PATH)
        header_list = self.list_queue.get()
        snippet = ''
        snippet += "Mailbox: " + header_list[1][0]["To"] + '\n\n'
        snippet += "{:<8}\t{:^30}\t\t{:^40}\t\t{:^15}\n".format(
            "ID", "From", "Subject", "Time & Date")
        header_list = zip(header_list[0], header_list[1])
        for msg in reversed(list(header_list)):
            mail_id = msg[0]
            mail_subject = msg[1]["subject"]
            mail_from = msg[1]["From"]
            mail_date = msg[1]["Date"]
            if len(mail_subject) > 60:
                mail_subject = mail_subject[:57] + '...'
            first_line, second_line = split_line(mail_subject)
            snippet += "{:<8}\t{:<30}\t\t{:<40}\t\t{:^15}\n".format(
                mail_id, mail_from[:30], first_line, mail_date[:11])
            snippet += "{:<8}\t{:<30}\t\t{:<40}\t\t{:^15}\n".format(
                '', '', second_line, mail_date[11:])
        snippet += "\n"
        self.view.run_command("insert_snippet", {"contents": snippet})
        print("OauthMail >>> Mail list acquired.")


class PrintMailInView(threading.Thread):
    def __init__(self, mail_queue, view):
        super(PrintMailInView, self).__init__(self)
        self.mail_queue = mail_queue
        self.view = view

    def run(self):
        msg = self.mail_queue.get()
        snippet = ""
        snippet += "From   : {}\n".format(msg['address'])
        snippet += "To     : {}\n".format(msg["to"])
        snippet += "Cc     : {}\n".format(msg["cc"])
        snippet += "Bcc    : {}\n".format(msg["bcc"])
        snippet += "Subject: {}\n".format(msg["subject"])
        snippet += "\n"
        snippet += "{}\n".format(msg["body"])
        self.view.run_command("insert_snippet", {"contents": snippet})
        print("OauthMail >>> Mail acquired.")
