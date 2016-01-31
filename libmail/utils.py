from . import mailconf
from . import settinghandler
import sublime
import queue
import re
from time import sleep
from time import time
from .quicklog import QuickLog
import mimetypes
from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
# Set YAML flags and global variable _LOADED_SETTINGS

# _LOADED_SETTINGS = None
# _SETTING_FILE = "QuickMail.sublime-settings"
SENDER_FLAG = 'meta.address.sender string'
ATTACHMENT_FLAG = 'meta.attachment string'
SUBJECT_FLAG = 'meta.subject string'
MAIL_PREFIX_FLAG = 'text.email '
MESSAGE_FLAG = 'meta.message'
PANEL_LOCK = False

VIEW_TO_MAIL = {}
ID_TO_IMAP = {}


def init_mailbox_queue():
    for mailbox in get_mailbox_list():
        ID_TO_IMAP[mailbox["identity"]] = queue.Queue()


def RECIPIENTS_FLAG(typ):
    """
    Since there are at least three types of recipients flags :CC BCC and To
    so, define a function here instead of three constants.
    """
    return 'meta.address.recipient.{0} string'.format(typ)


SUCCESS_MESSAGE = "Message Successfully Sent."
FAIL_MESSAGE = "Message failed."
MAIL_CLASS_DICT = {
    "gmail": mailconf.google_account,
    "outlook": mailconf.outlook_account,
    "generic": mailconf.pass_account
}


def wait_lock(waiting_time=None):
    if not waiting_time:
        waiting_time = 2

    def _wait_lock(function):
        def wrapp(*args):
            global PANEL_LOCK
            current_time = int(time())
            time_limit = current_time + waiting_time
            while current_time < time_limit:
                if not PANEL_LOCK:
                    PANEL_LOCK = True
                    function(*args)
                    PANEL_LOCK = False
                    break
                else:
                    sleep(0.1)
                    current_time += 0.1
            else:
                PANEL_LOCK = False
                raise ValueError("Time Out!")
        return wrapp
    return _wait_lock


def get_all_content(view):
    selected = ""
    for r in view.sel():
        selected += view.substr(r)
        if selected and not selected.endswith("\n"):
            selected += "\n"

    if not selected:
        selected = view.substr(sublime.Region(0, view.size()))
    return selected


def get_all_recipients(view):
    pass


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
            QuickLog.log("" + name + " Mailbox detected")
            return name
    QuickLog.log(" Not an QuickMail, will need Username/Password.")
    return "generic"


@wait_lock(5)
def show_mailbox_panel(window, on_done):
    mailbox_list = get_mailbox_list()
    entries = get_panel_entry_list(mailbox_list)
    window.show_quick_panel(entries, on_done)


def swap_on_top(lst, idx_lst):
    priority_items = []
    for idx in idx_lst:
        priority_items.append(lst.pop(idx))
    priority_items.extend(lst)
    return priority_items


def get_mailbox_list():
    _SETTINGS = settinghandler.get_settings()
    mailbox_list = _SETTINGS.get_mailbox_list()
    default_mailbox_idx = [mailbox_list.index(mailbox) for mailbox in mailbox_list
                           if mailbox["parameters"]["default"] == "yes"]
    mailbox_list = swap_on_top(mailbox_list, default_mailbox_idx)
    return mailbox_list


def get_panel_entry_list(mailbox_list):
    return [[mailbox["identity"], "authentication method: {}".format(mailbox["authentication"])]
            for mailbox in mailbox_list]


def attach(attachments, message_info):
    for path in attachments:
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
        return message_info


def where_is_me(view):
    pass
