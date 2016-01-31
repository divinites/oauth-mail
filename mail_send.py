import os
from .libmail.utils import *
from .libmail import settinghandler
from .libmail.quicklog import QuickLog
import sublime_plugin
import threading
import sublime
import re
from time import sleep
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class SendMailThread(threading.Thread):
    def __init__(self, msg, identity, recipients):
        threading.Thread.__init__(self)
        self.msg = msg
        self.recipients = recipients
        self.identity = identity

    def run(self):

        mail_type = check_mailbox_type(self.identity)
        account = MAIL_CLASS_DICT[mail_type](self.identity)

        QuickLog.log("" + self.identity + " Account object realized.")
        account.start_smtp(account.smtp_server, account.smtp_port,
                           account.tls_flag)
        QuickLog.log("Successfully connect SMTP server, ready to sent!")
        sleep(10)
        if account.smtp_authenticate():
            QuickLog.log("Start Sending email...")
            account.send_mail(self.identity, self.recipients, self.msg)
            QuickLog.log("Succeeded.")
            sublime.status_message(SUCCESS_MESSAGE)
        else:
            QuickLog.log("failed.")
            sublime.status_message(FAIL_MESSAGE)


class MailSendCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        view = self.window.active_view()
        if not view:
            return False
        regions = view.find_by_selector(MAIL_PREFIX_FLAG)
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
            regions = view.find_by_selector(MAIL_PREFIX_FLAG + selector)
            result = joiner.join([view.substr(r) for r in regions])
            return result

        # get identity
        if _SETTINGS.show_prompt():
            view.run_command("show_panel", {"panel": "output.exec"})
        identity = get_text(SENDER_FLAG).strip()
        message = get_text(MESSAGE_FLAG)
        if message.startswith('#!'):
            message = message.split("\n", 1)[1]

        # compose message
        content = MIMEText(message, "plain")

        attachments = []
        for r in view.find_by_selector(ATTACHMENT_FLAG):
            attachment = view.substr(r)
            if not os.path.exists(attachment):
                sublime.error_message("Attachment does not exist: %s" %
                                      attachment)
                return
            attachments.append(attachment)

        message_info = MIMEMultipart()
        message_info['Subject'] = get_text(SUBJECT_FLAG)
        message_info.attach(content)
        if attachments:
            message_info = attach(attachments, message_info)
        recipients = []
        for typ in ('to', 'cc', 'bcc'):
            rcpt = get_text(RECIPIENTS_FLAG(typ), joiner=", ")
            if not rcpt:
                continue
            recipients += [x for x in re.split(r",\s*", str(rcpt))]

            if typ == 'bcc':
                continue
            message_info[typ.capitalize()] = rcpt
            QuickLog.log("Message prepared.")
            mail_thread = SendMailThread(message_info, identity, recipients)
            mail_thread.start()
