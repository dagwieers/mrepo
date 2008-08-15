#!/usr/bin/python
#
# $Id: up2dateLog.py 87091 2005-11-15 17:25:11Z alikins $

import time
import string
import config

class Log:
    """
    attempt to log all interesting stuff, namely, anything that hits
    the network any error messages, package installs, etc
    """ # " emacs sucks
    def __init__(self):
        self.app = "up2date"
        self.cfg = config.initUp2dateConfig()
        

    def log_debug(self, *args):
        if self.cfg["debug"] > 1:
            apply(self.log_me, args, {})
            if self.cfg["isatty"]:
                print "D:", string.join(map(lambda a: str(a), args), " ")
                
    def log_me(self, *args):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
	s = ""
        for i in args:
            s = s + "%s" % (i,)
        self.write_log(s)

    def trace_me(self):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
        import traceback
        x = traceback.extract_stack()
        bar = string.join(traceback.format_list(x))
        self.write_log(bar)

    def log_exception(self, type, value, tb):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
        import traceback
        x = traceback.extract_tb(tb)
        bar = string.join(traceback.format_list(x))
        # all of the exception we raise include an errmsg string
        if hasattr(value, "errmsg"):
            self.write_log(value.errmsg)
        self.write_log(bar)
        
    def write_log(self, s):
        
        log_name = self.cfg["logFile"] or "/var/log/up2date"
        log_file = open(log_name, 'a')
        msg = "%s %s\n" % (self.log_info, str(s))
        log_file.write(msg)
        log_file.flush()
        log_file.close()

def initLog():
    global log
    try:
        log = log
    except NameError:
        log = None

    if log == None:
        log = Log()

    return log
