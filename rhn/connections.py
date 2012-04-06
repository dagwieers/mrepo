#/usr/bin/env python
#
# Connection objects
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>

# $Id: connections.py 191145 2010-03-01 10:21:24Z msuchy $


import sys
import string
import SSL
import nonblocking

import httplib
import xmlrpclib

# Import into the local namespace some httplib-related names
_CS_REQ_SENT = httplib._CS_REQ_SENT
_CS_IDLE = httplib._CS_IDLE
ResponseNotReady = httplib.ResponseNotReady

class HTTPResponse(httplib.HTTPResponse):
    def set_callback(self, rs, ws, ex, user_data, callback):
        if not isinstance(self.fp, nonblocking.NonBlockingFile):
            self.fp = nonblocking.NonBlockingFile(self.fp)
        self.fp.set_callback(rs, ws, ex, user_data, callback)

    # Fix a bug in the upstream read() method - partial reads will incorrectly
    # update self.length with the intended, not the real, amount of bytes
    # See http://python.org/sf/988120
    def read(self, amt=None):
        if self.fp is None:
            return ''

        if self.chunked:
            return self._read_chunked(amt)

        if amt is None:
            # unbounded read
            if self.will_close:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)

        if self.length is not None:
            # Update the length with the amount of bytes we actually read
            self.length = self.length - len(s)

        return s


class HTTPConnection(httplib.HTTPConnection):
    response_class = HTTPResponse
    
    def __init__(self, host, port=None):
        httplib.HTTPConnection.__init__(self, host, port)
        self._cb_rs = []
        self._cb_ws = []
        self._cb_ex = []
        self._cb_user_data = None
        self._cb_callback = None
        self._user_agent = "rhn.connections $Revision: 191145 $ (python)"

    def set_callback(self, rs, ws, ex, user_data, callback):
        # XXX check the params
        self._cb_rs = rs
        self._cb_ws = ws
        self._cb_ex = ex
        self._cb_user_data = user_data
        self._cb_callback = callback

    def set_user_agent(self, user_agent):
        self._user_agent = user_agent

    # XXX Had to copy the function from httplib.py, because the nonblocking
    # framework had to be initialized
    def getresponse(self):
        "Get the response from the server."

        # check if a prior response has been completed
        if self.__response and self.__response.isclosed():
            self.__response = None

        #
        # if a prior response exists, then it must be completed (otherwise, we
        # cannot read this response's header to determine the connection-close
        # behavior)
        #
        # note: if a prior response existed, but was connection-close, then the
        # socket and response were made independent of this HTTPConnection
        # object since a new request requires that we open a whole new
        # connection
        #
        # this means the prior response had one of two states:
        #   1) will_close: this connection was reset and the prior socket and
        #                  response operate independently
        #   2) persistent: the response was retained and we await its
        #                  isclosed() status to become true.
        #
        if self.__state != _CS_REQ_SENT or self.__response:
            raise ResponseNotReady()

        if self.debuglevel > 0:
            response = self.response_class(self.sock, self.debuglevel)
        else:
            response = self.response_class(self.sock)
        
        # The only modification compared to the stock HTTPConnection
        if self._cb_callback:
            response.set_callback(self._cb_rs, self._cb_ws, self._cb_ex,
                self._cb_user_data, self._cb_callback)

        response.begin()
        assert response.will_close != httplib._UNKNOWN
        self.__state = _CS_IDLE

        if response.will_close:
            # this effectively passes the connection to the response
            self.close()
        else:
            # remember this, so we can tell when it is complete
            self.__response = response

        return response


class HTTPProxyConnection(HTTPConnection):
    def __init__(self, proxy, host, port=None, username=None, password=None):
        # The connection goes through the proxy
        HTTPConnection.__init__(self, proxy)
        # save the proxy values
        self.__proxy, self.__proxy_port = self.host, self.port
        # self.host and self.port will point to the real host
        self._set_hostport(host, port)
        # save the host and port
        self._host, self._port = self.host, self.port
        # Authenticated proxies support
        self.__username = username
        self.__password = password

    def connect(self):
        # We are actually connecting to the proxy
        self._set_hostport(self.__proxy, self.__proxy_port)
        HTTPConnection.connect(self)
        # Restore the real host and port
        self._set_hostport(self._host, self._port)

    def putrequest(self, method, url, skip_host=0):
        # The URL has to include the real host
        hostname = self._host
        if self._port != self.default_port:
            hostname = hostname + ':' + str(self._port)
        newurl = "http://%s%s" % (hostname, url)
        # Piggyback on the parent class
        HTTPConnection.putrequest(self, method, newurl, skip_host=skip_host)
        # Add proxy-specific headers
        self._add_proxy_headers()
        
    def _add_proxy_headers(self):
        if not self.__username:
            return
        # Authenticated proxy
        import base64
        userpass = "%s:%s" % (self.__username, self.__password)
        enc_userpass = string.replace(base64.encodestring(userpass), "\n", "")
        self.putheader("Proxy-Authorization", "Basic %s" % enc_userpass)
        
class HTTPSConnection(HTTPConnection):
    response_class = HTTPResponse
    default_port = httplib.HTTPSConnection.default_port

    def __init__(self, host, port=None, trusted_certs=None):
        HTTPConnection.__init__(self, host, port)
        trusted_certs = trusted_certs or []
        self.trusted_certs = trusted_certs

    def connect(self):
        "Connect to a host on a given (SSL) port"
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.sock = SSL.SSLSocket(sock, self.trusted_certs)
        self.sock.init_ssl()

class HTTPSProxyResponse(HTTPResponse):
    def begin(self):
        HTTPResponse.begin(self)
        self.will_close = 0

class HTTPSProxyConnection(HTTPProxyConnection):
    default_port = HTTPSConnection.default_port

    def __init__(self, proxy, host, port=None, username=None, password=None, 
            trusted_certs=None):
        HTTPProxyConnection.__init__(self, proxy, host, port, username, password)
        trusted_certs = trusted_certs or []
        self.trusted_certs = trusted_certs

    def connect(self):
        # Set the connection with the proxy
        HTTPProxyConnection.connect(self)
        # Use the stock HTTPConnection putrequest 
        host = "%s:%s" % (self._host, self._port)
        HTTPConnection.putrequest(self, "CONNECT", host)
        # Add proxy-specific stuff
        self._add_proxy_headers()
        # And send the request
        HTTPConnection.endheaders(self)
        # Save the response class
        response_class = self.response_class
        # And replace the response class with our own one, which does not
        # close the connection after 
        self.response_class = HTTPSProxyResponse
        response = HTTPConnection.getresponse(self)
        # Restore the response class
        self.response_class = response_class
        # Close the response object manually
        response.close()
        if response.status != 200:
            # Close the connection manually
            self.close()
            raise xmlrpclib.ProtocolError(host,
                response.status, response.reason, response.msg)
        self.sock = SSL.SSLSocket(self.sock, self.trusted_certs)
        self.sock.init_ssl()

    def putrequest(self, method, url, skip_host=0):
        return HTTPConnection.putrequest(self, method, url, skip_host=skip_host)

    def _add_proxy_headers(self):
        HTTPProxyConnection._add_proxy_headers(self)
        # Add a User-Agent header
        self.putheader("User-Agent", self._user_agent)
