from requests_oauthlib.oauth2_session import OAuth2Session
from base64 import b64encode
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.parse import parse_qsl
import json
import os
import webbrowser
import http.server
import time
import re
from os.path import dirname
from os.path import realpath


_PACKAGE_PATH = dirname(dirname(dirname(realpath(__file__))))
_CACHE_PATH = os.path.join(_PACKAGE_PATH, "Packages/User/Oauthmail.cache")


def cache_path(file_name):
    return os.path.join(_CACHE_PATH, file_name)


def find_type(client_secret_file):
    app_type = ''
    for key in client_secret_file.keys():
        app_type = key
    return app_type


class OauthMailSession(OAuth2Session):
    def __init__(self,
                 client_id=None,
                 client=None,
                 auto_refresh_url=None,
                 auto_refresh_kwargs=None,
                 scope=None,
                 redirect_uri=None,
                 token=None,
                 state=None,
                 token_updater=None,
                 client_secret_json_file=None,
                 client_secret=None,
                 auth_uri=None,
                 token_uri=None,
                 cache_flag=True, **kwargs):
        _client_id = None
        if not os.path.exists(_CACHE_PATH):
            os.makedirs(_CACHE_PATH)
        if client_secret_json_file:
            with open(client_secret_json_file, 'r') as f:
                secret_file = json.load(f)
            _type = find_type(secret_file)
            for key, value in secret_file[_type].items():
                if key == "client_id":
                    _client_id = value
                if key == "client_secret":
                    self.client_secret = value
                if key == "auth_uri":
                    self.auth_uri = value
                if key == "token_uri":
                    self.token_uri = value
        else:
            _client_id = client_id
            self.client_secret = client_secret
            self.auth_uri = auth_uri
            self.token_uri = token_uri

        super(OauthMailSession, self).__init__(
            _client_id, client, auto_refresh_url, auto_refresh_kwargs, scope,
            redirect_uri, token, state, token_updater)
        self.acquired_time = None
        self.expires_in = None
        self.cache_file = None
        self.cache_flag = cache_flag

    def _token_is_cached(self):
        target = b64encode((self.client_id).encode('utf-8')).decode("utf-8")
        filepaths = os.listdir(_CACHE_PATH)
        if target in filepaths:
            self.cache_file = target
            return True
        else:
            return False

    def _token_expired(self):
        if self.expires_in + self.acquired_time - 10 < time.time():
            return True
        else:
            return False

    def _load_cached_token(self):
        if self._token_is_cached() is True:
            with open(cache_path(self.cache_file), 'r') as cache_file:
                root = json.load(cache_file)
                self.token["access_token"] = root["access_token"]
                self.acquired_time = root["acquired_time"]
                self.expires_in = root["expires_in"]
                if "refresh_token" in root.keys():
                    self.token["refresh_token"] = root["refresh_token"]
        else:
            return

    def _save_in_cache(self):
        if self.token:
            root = {}
            root["access_token"] = self.token["access_token"]
            root["refresh_token"] = self.token["refresh_token"]
            root["expires_in"] = self.expires_in
            root["acquired_time"] = time.time()
            self.acquired_time = root["acquired_time"]
            self.cache_file = b64encode(self.client_id.encode("utf-8")).decode(
                "utf-8")

            with open(cache_path(self.cache_file), 'w') as cache_file:
                json.dump(root, cache_file)
        else:
            return

    def _generate_auth_url(self, **kwargs):
        return self.authorization_url(url=self.auth_uri, **kwargs)

    def _acquire_code(self, **kwargs):
        def get_host_parameters(uri):
            queue = re.split(':', uri, flags=re.IGNORECASE)
            if queue[0] == "http" or queue[0] == "https":
                queue[1] = re.sub("//", '', queue[1])
                queue.pop(0)
            queue[1] = re.sub('/', '', queue[1])
            return (queue[0], int(queue[1]))

        host_params = get_host_parameters(self.redirect_uri)
        httpd = None
        while not httpd:
            try:
                httpd = RedirectServer(host_params, RedirectHandler)
            except:
                host_params = list(host_params)
                host_params[1] += 1
                host_params = tuple(host_params)
        self.redirect_uri = "http://" + host_params[0] + ":" + str(
            host_params[1])
        auth_url = self._generate_auth_url(**kwargs)[0]
        webbrowser.open(auth_url, new=1, autoraise=True)
        httpd.handle_request()
        code = httpd.query_params["code"]
        return code

    def _get_token(self, code, save=True):
        params = {}
        params['client_id'] = self.client_id
        params['client_secret'] = self.client_secret
        params['code'] = code
        params['redirect_uri'] = self.redirect_uri
        params['grant_type'] = 'authorization_code'
        response = urlopen(self.token_uri,
                           urlencode(params).encode('utf-8')).read()
        root = json.loads(response.decode('utf-8'))
        self.token["access_token"] = root["access_token"]
        self.token["refresh_token"] = root["refresh_token"]
        self.expires_in = root["expires_in"]
        if save is True:
            self._save_in_cache()

    def _refresh_token(self, save=True):
        params = {}
        params['client_id'] = self.client_id
        params['client_secret'] = self.client_secret
        params['refresh_token'] = self.token["refresh_token"]
        params['grant_type'] = 'refresh_token'
        response = urlopen(self.token_uri,
                           urlencode(params).encode('utf-8')).read()
        root = json.loads(response.decode('utf-8'))
        self.token["access_token"] = root["access_token"]
        self.expires_in = root["expires_in"]
        root["acquired_time"] = time.time()
        if "refresh_token" in root.keys():
            self.token["refresh_token"] = root["refresh_token"]
        root["refresh_token"] = self.token["refresh_token"]
        self.acquired_time = root["acquired_time"]
        if save is True:
            self._save_in_cache()

    def gen_auth_string(self, identity, base64_encode=False):
        if self.acquired_time and self.expires_in:
            if self._token_expired():
                self._refresh_token(True)
        authstr = 'user={0}\1auth=Bearer {1}\1\1'.format(
            identity, self.token["access_token"])
        if base64_encode:
            authstr = b64encode(_encode(authstr)).decode("utf-8")
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
