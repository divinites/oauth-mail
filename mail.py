import sys
import os
cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(cwd)
os.chdir(cwd)
import mail2account
import sublime_plugin
import threading
import sublime
import re

_SETTING_FILE = "mail.sublime-settings"
_SENDER_FLAG = 'meta.address.sender string'
_ATTACHMENT_FLAG = 'meta.attachment string'
_SUBJECT_FLAG = 'meta.subject string'
_MAIL_PREFIX_FLAG = 'text.email '
_MESSAGE_FLAG = 'meta.message'
_SYNTAX_PATH = "Packages/sublime-mail/mail.tmLanguage"
_SUCCESS_MESSAGE = "Message Successfully Sent."

_MAIL_CLASS_DICT = {"gmail":
                    {
                        "smtp": mail2account.GoogleSender,
                        "imap": mail2account.GoogleReceiver
                    },

                    "outlook":
                    {
                        "smtp": mail2account.OutlookSender,
                        "imap": mail2account.OutlookReceiver
                    },

                    "generic":
                    {
                        "smtp": mail2account.GenericSender,
                        "imap": mail2account.GenericReceiver
                    }
                    }


def _RECIPIENTS_FLAG(typ):
    return 'meta.address.recipient.{0} string'.format(typ)


class MailWriteCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    def run(self, From="", To="", Cc="", Bcc="", Subject="",
            Body="", Signature=None, Attachments=[]):

        view = self.window.new_file()
        settings = mail2account.SettingHandler(_SETTING_FILE)
        view.set_syntax_file(_SYNTAX_PATH)
        snippet = ""
        snippet += "From   : ${1:%s}\n" % settings.get_default_identity()
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

        def check_mailbox_type(identity):
            checker_dict = {"outlook": "\S+@[live|hotmail].+",
                            "gmail": "\S+@[gmail|googlemail].+"}
            for name, checker in checker_dict.items():
                prog = re.compile(checker)
                result = prog.match(identity)
                if result:
                    return name
            return "generic"

        mail_type = check_mailbox_type(self.identity)

        account = _MAIL_CLASS_DICT[mail_type]["smtp"](_SETTING_FILE,
                                                      self.identity)
        if account.smtp_authenticate():
            account.send_mail(self.recipients, self.msg)

#        self.server_account.authenticate(0)
#        try:
#            self.server_account.send_mail(self.recipients,
#                                          self.msg.as_string())
#        except Exception as e:
#            sublime.error_message("Sending failed: %s" % e)
        sublime.status_message(_SUCCESS_MESSAGE)


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

        view = self.window.active_view()

        def get_text(selector, joiner=" "):
            regions = view.find_by_selector(_MAIL_PREFIX_FLAG+selector)
            result = joiner.join([view.substr(r) for r in regions])
            return result

        # get identity
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
                sublime.error_message("Attachment does not exist: %s"
                                      % attachment)
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
                msg.add_header('Content-Disposition', 'attachment',
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
            mail_thread = SendMailThread(message_info, identity, recipients)
            mail_thread.start()


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

        self.window.run_command('email_write',
                                {'Attachments': [view.file_name()]})


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

        split_line = "-"*20+"\n"

        self.window.run_command('mail_write', {'Body': split_line+selected})
