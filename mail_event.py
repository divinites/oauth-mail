import sublime_plugin
from .libmail.quicklog import QuickLog
from .libmail.utils import *


class MailListenerCommand(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        if view.id() in VIEW_TO_MAIL.keys():
            del VIEW_TO_MAIL[view.id()]
            QuickLog.log("View ID " + str(view.id()) + " is deleted from VIEW_TO_MAIL directory.")
            QuickLog.log("VIEW_TO_MAIL now has " + str(list(VIEW_TO_MAIL.keys())))


