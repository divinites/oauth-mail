from .libmail.utils import *
from .libmail import settinghandler
from .libmail.quicklog import QuickLog
import sublime_plugin
import threading
import sublime
import queue
from email.utils import parseaddr
from datetime import date
from datetime import timedelta

LIST_SYNTAX_PATH = "Packages/{}/list.tmLanguage".format(__package__)
LIST_THEME_PATH = "Packages/{}/list.tmTheme".format(__package__)
MAIL_SYNTAX_PATH = "Packages/{}/mail.tmLanguage".format(__package__)


class ShowMailCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    def on_done(self, mail_id):
        content = get_all_content(self.window.active_view())
        first_line = content.splitlines()[0]
        identity = parseaddr(first_line)[1]
        if ID_TO_IMAP[identity].empty():
            IMAP_thread = MailBoxConnectionThread(identity)
            QuickLog.log("IMAP thread established.")
            IMAP_thread.start()
        else:
            QuickLog.log("Use previous mailbox object.")
        mail_queue = queue.Queue()
        fetch_mail = FetchMailThread(identity, mail_id, mail_queue)
        QuickLog.log("Fetching mails...")
        fetch_mail.start()
        print_in_view = PrintMailInView(mail_queue)
        print_in_view.start()

    def run(self):
        sublime.active_window().run_command('hide_panel')
        sublime.active_window().show_input_panel('Mail ID:', '', self.on_done,
                                                 None, None)


class ListRecentMailCommand(sublime_plugin.WindowCommand):
    def is_enable(self):
        return True

    def run(self):
        self.window.run_command("show_panel", {"panel": "console", "toggle": "true"})
        self.mailbox_list = get_mailbox_list()
        show_mailbox_panel(self.window, self._on_panel_selection)

    def _on_panel_selection(self, selection):
        if selection >= 0:
            self.window.run_command("connect_mailbox", {"identity": self.mailbox_list[selection]["identity"]})


class ConnectMailboxCommand(sublime_plugin.WindowCommand):
    def run(self, identity):
        _SETTINGS = settinghandler.get_settings()
        list_period = _SETTINGS.get_list_period()
        since_date = date.today() - timedelta(days=list_period)
        date_string = "(SINCE \"" + since_date.strftime("%d-%b-%Y") + "\")"
        if ID_TO_IMAP[identity].empty():
            QuickLog.log("establish a new connection...")
            IMAP_thread = MailBoxConnectionThread(identity)
            IMAP_thread.start()
        list_queue = queue.Queue()
        list_mail = GetEmailListThread(identity, list_queue, date_string, None)
        list_mail.start()
        print_in_view = PrintListInView(identity, list_queue)
        print_in_view.start()


class MailBoxConnectionThread(threading.Thread):
    def __init__(self, identity):
        threading.Thread.__init__(self)
        self.identity = identity
        self.mailbox = MAIL_CLASS_DICT[check_mailbox_type(identity)](identity)

    def run(self):
        self.mailbox.start_imap(self.mailbox.imap_server,
                                self.mailbox.imap_port, self.mailbox.tls_flag)
        self.authenticate()
        QuickLog.log(" Mailbox connected.")

    @wait_lock(5)
    def authenticate(self):
        if self.mailbox.imap_authenticate():
            QuickLog.log("IMAP thread established.")
            ID_TO_IMAP[self.identity].put(self.mailbox)


class GetEmailListThread(threading.Thread):
    def __init__(self,
                 identity,
                 out_list_queue,
                 date_string,
                 location=None):
        threading.Thread.__init__(self)
        self.identity = identity
        self.list_queue = out_list_queue
        self.date_string = date_string
        if location is None:
            self.location = 'INBOX'
        else:
            self.location = location

    def run(self):
        self.get_mail_list()
        QuickLog.log("Mail list acquired.")

    def get_mail_list(self):
        mailbox = ID_TO_IMAP[self.identity].get()
        mail_list = mailbox.fetch_header_list(self.date_string)
        QuickLog.log("Fetching mail headers...")
        self.list_queue.put(mail_list)
        ID_TO_IMAP[self.identity].put(mailbox)


class FetchMailThread(threading.Thread):
    def __init__(self,
                 identity=None,
                 email_id=None,
                 out_mail_queue=None,
                 location=None):
        threading.Thread.__init__(self)
        self.email_id = email_id
        self.identity = identity
        self.mail_queue = out_mail_queue
        self.body = None
        if location is None:
            self.location = 'INBOX'

    def run(self):
        mailbox = ID_TO_IMAP[self.identity].get()
        msg = mailbox.fetch_email(self.email_id, self.location)
        QuickLog.log("Mail Fetched.")
        self.mail_queue.put(msg)
        ID_TO_IMAP[self.identity].put(mailbox)


class PrintListInView(threading.Thread):
    def __init__(self, identity, list_queue):
        super(PrintListInView, self).__init__(self)
        self.list_queue = list_queue
        self.identity = identity

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

        header_list = self.list_queue.get()
        snippet = ''
        snippet += "Mailbox: " + self.identity + '\n\n'
        snippet += "{:<8}\t{:^30}\t\t{:^40}\t\t{:^15}\n".format(
            "ID", "From", "Subject", "Time & Date")
        header_list = zip(header_list[0], header_list[1])
        for msg in reversed(list(header_list)):
            mail_id = msg[0]
            mail_subject = msg[1]["subject"]
            mail_from = parseaddr(msg[1]["From"])
            mail_date = msg[1]["Date"]
            if len(mail_subject) > 60:
                mail_subject = mail_subject[:57] + '...'
            first_line, second_line = split_line(mail_subject)
            snippet += "{:<8}\t{:<30}\t\t{:<40}\t\t{:^15}\n".format(
                mail_id, mail_from[0], first_line, mail_date[:11])
            snippet += "{:<8}\t{:<30}\t\t{:<40}\t\t{:^15}\n".format(
                '', mail_from[1], second_line, mail_date[11:])
        snippet += "\n"
        view = sublime.active_window().new_file()
        view.set_syntax_file(LIST_SYNTAX_PATH)
        view.settings().set('color_scheme', LIST_THEME_PATH)
        view.run_command("insert_snippet", {"contents": snippet})
        QuickLog.log("Mail list printed.")


class PrintMailInView(threading.Thread):
    def __init__(self, mail_queue):
        super(PrintMailInView, self).__init__(self)
        self.mail_queue = mail_queue

    def run(self):
        msg = self.mail_queue.get()
        view = sublime.active_window().new_file()
        VIEW_TO_MAIL[view.id()] = msg
        snippet = ""
        snippet += "From   : {}\n".format(msg['address'])
        snippet += "To     : {}\n".format(msg["to"])
        snippet += "Cc     : {}\n".format(msg["cc"])
        snippet += "Bcc    : {}\n".format(msg["bcc"])
        snippet += "Subject: {}\n".format(msg["subject"])
        snippet += "\n"
        snippet += "{}\n".format(msg["body"])
        view.set_syntax_file(MAIL_SYNTAX_PATH)
        view.run_command("insert_snippet", {"contents": snippet})
        QuickLog.log("Mail printed.")


def plugin_loaded():
    init_mailbox_queue()
