from base64 import b64encode
import json
import os
import sublime
from os.path import dirname
from os.path import realpath


_PACKAGE_PATH = dirname(dirname(dirname(realpath(__file__))))
_CACHE_PATH = os.path.join(_PACKAGE_PATH, "Packages/User/Oauthmail.cache")

def encrypt(strings):
	return b64encode((strings).encode('utf-8')).decode("utf-8")


def cache_path(file_name):
    return os.path.join(_CACHE_PATH, file_name)


class NormalMailSession:
	def __init__(self, identity):
		self.identity = identity
		self.username = None
		self.password = None
        self.cache_file = encrypt(self.identity)
		if not os.path.exists(_CACHE_PATH):
            os.makedirs(_CACHE_PATH)


    def _password_is_cached(self):
        target = b64encode((self.identity).encode('utf-8')).decode("utf-8")
        filepaths = os.listdir(_CACHE_PATH)
        if target in filepaths:
            self.cache_file = target
            return True
        else:
            return False

    def _load_cached_password(self):
        if self._password_is_cached() is True:
            with open(cache_path(self.cache_file), 'r') as cache_file:
                root = json.load(cache_file)
                self.password = root[encrypt("password")]
                self.username = root[encrypt("username")]
        else:
            return

    def _save_in_cache(self):
    	if self.password is not None and self.username is not None:
    		root = {}
    		root[encrypt("password")] = encrypt(self.password)
            root[encrypt("username")] = encrypt(self.username)
            with open(cache_path(self.cache_file), 'w') as cache_file:
                json.dump(root, cache_file)
        else:
            return

    def _get_username_password(self):
        sublime.active_window().run_command('hide_panel')
        sublime.active_window().show_input_panel('Enter your Username:', '', self.on_username_done,
                                                 None, None)
        sublime.active_window().run_command('hide_panel')
        sublime.active_window().show_input_panel('Enter your Password:', '', self.on_password_done,
                                                 None, None)

        def on_username_done(self, content):
            self.username = content

        def on_password_done(self, content):
            self.password = content








