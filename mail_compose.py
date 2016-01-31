from .libmail.utils import *
from .libmail import settinghandler
from .libmail.quicklog import QuickLog
import sublime_plugin
import sublime
from email.utils import parseaddr

MAIL_SYNTAX_PATH = "Packages/{}/mail.tmLanguage".format(__package__)
SPLIT_LINE = "-" * 20 + "\n"


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
        view.set_syntax_file(MAIL_SYNTAX_PATH)
        if not From:
            From = _SETTINGS.get_default_identity()
        snippet = ""
        snippet += "From   : ${1:%s}\n" % From
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


class MailReplyCommand(sublime_plugin.WindowCommand):
    def run(self, args):
        view = self.window.active_view()
        lines = view.split_by_newlines(sublime.Region(0, view.size()))
        replied_content = ""
        for idx, line in enumerate(lines):
            if idx == 0:
                original_from = parseaddr(view.substr(line))
                if args == "fwd":
                    original_from = ' ' * 2
            if idx == 1:
                original_to = parseaddr(view.substr(line))
            if idx == 2:
                original_cc = ' ' * 2
                if args == 'all':
                    original_cc = parseaddr(view.substr(line))
            if idx == 4:
                original_subject = view.substr(line)[8:]
            replied_content += "> " + view.substr(line) + "\n"
            PREFIX = "RE: " if args != "fwd" else "FWD: "
        if view.id() not in VIEW_TO_MAIL.keys():
            QuickLog.log("From the view text")
            self.window.run_command('mail_write', {'From': original_to[1],
                                                   'To': original_from[1],
                                                   'Cc': original_cc,
                                                   'Subject': PREFIX + original_subject,
                                                   'Body': SPLIT_LINE + replied_content})
        else:
            message = VIEW_TO_MAIL[view.id()]
            QuickLog.log("From message object")
            self.window.run_command('mail_write', {'From': message['to'],
                                                   'To': message['address'],
                                                   'Cc': original_cc,
                                                   'Subject': PREFIX + original_subject,
                                                   'Body': SPLIT_LINE + replied_content})


class MailReplyOneCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('mail_reply', {'args': 'normal'})


class MailReplyAllCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('mail_reply', {'args': 'all'})


class MailForwardCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('mail_reply', {"args": 'fwd'})


class AttachThisFileCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        view = self.window.active_view()
        if not view:
            return False
        regions = view.find_by_selector(MAIL_PREFIX_FLAG)
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
        QuickLog.log("File Attached.")


class SendAsMailCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        content = get_all_content(view)
        self.window.run_command('mail_write', {'Body': SPLIT_LINE + content})
