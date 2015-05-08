from urllib.parse import urlencode
from urllib.request import urlopen
import http.server
import base64
import urllib.request
import json
from urllib.parse import parse_qsl
import webbrowser
import os
import time
import sys
import re
cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(cwd)
os.chdir(cwd)

NECESSARY_PARAMETERS = ("client_secret", "auth_uri", "token_uri", "client_id")


def find_type(client_secret_file):
    app_type = ''
    for key in client_secret_file.keys():
        app_type = key
    return app_type


class OAuth2:
    def __init__(self,
                 client_secret_json_file=None,
                 client_id=None,
                 client_secret=None,
                 scope=None,
                 auth_uri=None,
                 token_uri=None,
                 redirect_uri=None):
        self.config = {}
        if client_secret_json_file is not None:
            with open(client_secret_json_file, 'r') as f:
                secret_file = json.load(f)
            _type = find_type(secret_file)

            for key, value in secret_file[_type].items():
                for name in NECESSARY_PARAMETERS:
                    self.config[name] = value
        else:
            if not client_id or not client_secret:
                raise EOFError("Please config your mail first.")
            else:
                self.config["client_id"] = client_id
                self.config["client_secret"] = client_secret
        self.config["auth_uri"] = auth_uri
        self.config["token_uri"] = token_uri
        self.config["redirect_uri"] = redirect_uri
        self.config["scope"] = scope
        self.access_token = None
        self.refresh_token = None
        self.acquired_time = None
        self.expires_in = None
        self.cache_file = None
        filepaths = os.listdir("./cache")
        target = base64.b64encode(self.config["client_id"].encode('utf-8'))
        for filename in filepaths:
            if filename == target.decode('utf-8'):
                self.cache_file = filename
                break
        if self.cache_file:
            self._load_cached_token()
            if self.expires_in + self.acquired_time - 10 < time.time():
                self._refresh_token()
        else:
            code = self._acquire_code()
            self._get_token(code)

    def _load_cached_token(self):
        with open("cache/" + self.cache_file, 'r') as cache_file:
            root = json.load(cache_file)
            self.access_token = root["access_token"]
            self.acquired_time = root["acquired_time"]
            self.expires_in = root["expires_in"]
            if "refresh_token" in root.keys():
                self.refresh_token = root["refresh_token"]

    def _save_in_cache(self, root):
        if not self.cache_file:
            self.cache_file = base64.b64encode(
                self.config["client_id"].encode("utf-8")).decode("utf-8")
        with open("cache/" + self.cache_file, 'w') as cache_file:
            json.dump(root, cache_file)

    def set_scope(self, scope):
        self.config["scope"] = scope

    def read_cache(self):
        self._get_cache_file("cache")

# Just replicate Google's API

    @staticmethod
    def url_add(url, text):
        return '{0}/{1}'.format(url, text)

    @staticmethod
    def url_escape(text):
        return urllib.request.quote(text, safe="~-._")

    @staticmethod
    def get_host_parameters(uri):
        queue = re.split(':', uri, flags=re.IGNORECASE)
        if queue[0] == "http" or queue[0] == "https":
            queue[1] = re.sub("//", '', queue[1])
            queue.pop(0)
        queue[1] = re.sub('/', '', queue[1])
        return (queue[0], int(queue[1]))

    @staticmethod
    def url_unescape(text):
        return urllib.request.unquote(text)

    def format_url(self, parameters):
        secret_slice = []
        for par in parameters.items():
            secret_slice.append("{0}={1}".format(par[0],
                                                 self.url_escape(par[1])))
        return "&".join(secret_slice)

    def _acquire_code(self, response_type='code', scope=None):
        if not scope:
            scope = self.config["scope"]
        host_params = self.get_host_parameters(self.config["redirect_uri"])
        httpd = RedirectServer(host_params, RedirectHandler)
        params = {}
        params['client_id'] = self.config["client_id"]
        params['redirect_uri'] = self.config['redirect_uri']
        params['scope'] = scope
        params['response_type'] = response_type
        authorization_url = '{0}?{1}'.format(self.config["auth_uri"],
                                             self.format_url(params))
        webbrowser.open(authorization_url, new=1, autoraise=True)
        httpd.handle_request()
        code = httpd.query_params["code"]
        return code

    def _get_token(self, code, save=True):
        params = {}
        params['client_id'] = self.config["client_id"]
        params['client_secret'] = self.config["client_secret"]
        params['code'] = code
        params['redirect_uri'] = self.config["redirect_uri"]
        params['grant_type'] = 'authorization_code'
        response = urlopen(self.config["token_uri"],
                           urlencode(params).encode('utf-8')).read()
        root = json.loads(response.decode('utf-8'))
        self.access_token = root["access_token"]
        if "refresh_token" in root.keys():
            self.refresh_token = root["refresh_token"]
        root["acquired_time"] = time.time()
        self.acquired_time = root["acquired_time"]
        if save is True:
            self._save_in_cache(root)

    def _refresh_token(self, save=True):

        params = {}
        params['client_id'] = self.config["client_id"]
        params['client_secret'] = self.config["client_secret"]
        params['refresh_token'] = self.refresh_token
        params['grant_type'] = 'refresh_token'
        response = urlopen(self.config["token_uri"],
                           urlencode(params).encode('utf-8')).read()
        root = json.loads(response.decode('utf-8'))
        self.access_token = root["access_token"]
        root["acquired_time"] = time.time()
        root["refresh_token"] = self.refresh_token
        self.acquired_time = root["acquired_time"]
        if save is True:
            self._save_in_cache(root)

    def gen_auth_string(self, username, base64_encode=False):
        if self.acquired_time and self.expires_in:
            if self.acquired_time + self.expires_in < time.time():
                self._refresh_token(True)
        authstr = 'user={0}\1auth=Bearer {1}\1\1'.format(username,
                                                         self.access_token)
        if base64_encode:
            authstr = base64.b64encode(_encode(authstr)).decode("utf-8")
        return authstr


class RedirectServer(http.server.HTTPServer):
    query_params = {}


def _encode(strings):
    return bytes(strings, "utf-8")


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        query = s.path.split('?', 1)[-1]
        query = dict(parse_qsl(query))
        s.server.query_params = query
        s.wfile.write(_encode("<html><head><title>Authrization"
                              " Status</title></head>"))
        s.wfile.write(_encode("<body><p>The authentication "
                              "flow has completed.</p>"))
        s.wfile.write(_encode("</body></html>"))

    def log_message(self, format, *args):
        pass
