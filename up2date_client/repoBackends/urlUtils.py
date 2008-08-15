#!/usr/bin/python

# a url handler for non rhnlib stuff, based _heavily_ on
# http://diveintomark.org/projects/feed_parser/
# by  "Mark Pilgrim <http://diveintomark.org/>"
#  "Copyright 2002-3, Mark Pilgrim"

import sys
import urllib2
import StringIO
import gzip
import time
import re

from up2date_client import up2dateErrors

BUFFER_SIZE=8092
class MiscURLHandler(urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
	#print "code: %s" % code
        if ((code / 100) == 3) and (code != 304):
            return self.http_error_302(req, fp, code, msg, headers)
        if ((code / 100) == 4) and (code not in [404]):
            return self.http_error_404(req, fp, code, msg, headers)
        from urllib import addinfourl
        infourl = addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
#        raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
        return infourl


    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        if not hasattr(infourl, "status"):
            infourl.status = code

        return infourl

    def http_error_301(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    def http_error_404(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPDefaultErrorHandler.http_error_default(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    def http_error_403(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPDefaultErrorHandler.http_error_default(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    http_error_300 = http_error_302
    http_error_307 = http_error_302

def open_resource(source, etag=None, modified=None, agent=None, referrer=None, startRange=None, endRange=None):
    """
    URI, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it must be a tuple of 9 integers
    as returned by gmtime() in the standard Python time module. This MUST
    be in GMT (Greenwich Mean Time). The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.
    """

    if hasattr(source, "read"):
        return source

    if source == "-":
        return sys.stdin

    if not agent:
        agent = USER_AGENT
        
    # try to open with urllib2 (to use optional headers)
    request = urllib2.Request(source)
    if etag:
        request.add_header("If-None-Match", etag)
    if modified:
        request.add_header("If-Modified-Since", format_http_date(modified))
    request.add_header("User-Agent", agent)
    if referrer:
        request.add_header("Referer", referrer)
        request.add_header("Accept-encoding", "gzip")
    start = 0
    if startRange:
        start = startRange
    end = ""
    if endRange:
        end = endRange
    if startRange or endRange:
        range = "bytes=%s-%s" % (start, end)
        print range
        request.add_header("Range", range)
                           
    opener = urllib2.build_opener(MiscURLHandler())
    #print request.headers
    opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
    #return opener.open(request)
    try:
        return opener.open(request)
    except OSError:
	print "%s not a valud URL" % source
        # source is not a valid URL, but it might be a valid filename
        pass
    except ValueError:
	print "%s is of an unknown URL type" % source
    	pass


    # try to open with native open function (if source is a filename)
    try:
        return open(source)
    except:
	print sys.exc_info()
	print sys.exc_type
        pass

    # huh, not sure I like that at all... probabaly need
    # to change this to returning a fd/fh and reading on it.
    # but shrug, this is just for local files anway... -akl
    # treat source as string
    return StringIO.StringIO(str(source))

def get_etag(resource):
    """
    Get the ETag associated with a response returned from a call to 
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify an ETag for the resource, this will return None.
    """

    if hasattr(resource, "info"):
        return resource.info().getheader("ETag")
    return None

def get_modified(resource):
    """
    Get the Last-Modified timestamp for a response returned from a call to
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify a Last-Modified timestamp, this function will return None.
    Otherwise, it returns a tuple of 9 integers as returned by gmtime() in
    the standard Python time module().
    """

    if hasattr(resource, "info"):
        last_modified = resource.info().getheader("Last-Modified")
        if last_modified:
            return parse_http_date(last_modified)
    return None

short_weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
long_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_http_date(date):
    """
    Formats a tuple of 9 integers into an RFC 1123-compliant timestamp as
    required in RFC 2616. We don't use time.strftime() since the %a and %b
    directives can be affected by the current locale (HTTP dates have to be
    in English). The date MUST be in GMT (Greenwich Mean Time).
    """

    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (short_weekdays[date[6]], date[2], months[date[1] - 1], date[0], date[3], date[4], date[5])

def parse_http_date2(date):
    # I'm linux only, so just use strptime()
    # attemp to parse out the Last-Modified time
    # It means I can continue to avoid the use of
    # regexs if at all possible as well :->
    try:
        return time.strptime(date, "%a, %d %b %Y %H:%M:%S GMT")
    except:
        try:
            return time.strptime(date, "%A, %d-%b-%y %H:%M:%S GMT")
        except:
            try:
                return time.strptime(date, "%a %b %d %H:%M:%S %Y")
            except:
                return None



rfc1123_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}), (?P<day>\d{2}) (?P<month>[A-Z][a-z]{2}) (?P<year>\d{4}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
rfc850_match = re.compile(r"(?P<weekday>[A-Z][a-z]+), (?P<day>\d{2})-(?P<month>[A-Z][a-z]{2})-(?P<year>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
asctime_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}) (?P<month>[A-Z][a-z]{2})  ?(?P<day>\d\d?) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) (?P<year>\d{4})").match

def parse_http_date(date):
    """
    Parses any of the three HTTP date formats into a tuple of 9 integers as
    returned by time.gmtime(). This should not use time.strptime() since
    that function is not available on all platforms and could also be
    affected by the current locale.
    """

    date = str(date)
    year = 0
    weekdays = short_weekdays

    m = rfc1123_match(date)
    if not m:
        m = rfc850_match(date)
        if m:
            year = 1900
            weekdays = long_weekdays
        else:
            m = asctime_match(date)
            if not m:
                return None

    try:
        year = year + int(m.group("year"))
        month = months.index(m.group("month")) + 1
        day = int(m.group("day"))
        hour = int(m.group("hour"))
        minute = int(m.group("minute"))
        second = int(m.group("second"))
        weekday = weekdays.index(m.group("weekday"))
        a = int((14 - month) / 12)
        julian_day = (day - 32045 + int(((153 * (month + (12 * a) - 3)) + 2) / 5) + int((146097 * (year + 4800 - a)) / 400)) - (int((146097 * (year + 4799)) / 400) - 31738) + 1
        daylight_savings_flag = 0
        return (year, month, day, hour, minute, second, weekday, julian_day, daylight_savings_flag)
    except:
        # the month or weekday lookup probably failed indicating an invalid timestamp
        return None

def get_size(resource):
    if hasattr(resource, "info"):
        size = resource.info().getheader("Content-Length")
        if size == None:
            return size
        # packages can be big
        return long(size)
    return None


def readFDBuf(fd, progressCallback = None):
    # Open the storage file
    
    buf = ""

    size = get_size(fd)
    if size == None:
        return None
    size_read = 0
    while 1:
        chunk = fd.read(BUFFER_SIZE)
        l = len(chunk)
        if not l:
            break
        size_read = size_read + l
        buf = buf + chunk
        if progressCallback:
            progressCallback(size_read,size) 
    return buf



def readFDBufWriteFD(fd, writefd, progressCallback = None):
    # Open the storage file
    
    buf = ""

    startTime = time.time()
    lastTime = startTime
    
    size = get_size(fd)
    if size == None:
        return None

    size_read = 0
    while 1:
        curTime = time.time()
        chunk = fd.read(BUFFER_SIZE)
        l = len(chunk)
        if not l:
            break
        size_read = size_read + l
        amt = size - size_read
        if progressCallback:
            if curTime - lastTime >= 1 or amt == 0:
                lastTime = curTime
                bytesRead = float(size - amt)
                # if amt == 0, on a fast machine it is possible to have 
                # curTime - lastTime == 0, so add an epsilon to prevent a division
                # by zero
                speed = bytesRead / ((curTime - startTime) + .000001)
                if size == 0:
                    secs = 0
                else:
                    # speed != 0 because bytesRead > 0
                    # (if bytesRead == 0 then origsize == amt, which means a read
                    # of 0 length; but that's impossible since we already checked
                    # that l is non-null
                    secs = amt / speed
                progressCallback(size_read, size, speed, secs)
        writefd.write(chunk)
    writefd.flush()
    writefd.seek(0,0)
    
    return 1

# need to add callbacks at some point
def fetchUrl(url, progressCallback=None, msgCallback=None,
             lastModified=None, agent=None, start=None, end=None):
    fh = open_resource(url, modified=lastModified,
                       agent = agent, startRange=start,
                       endRange=end)

    if hasattr(fh,'status'):
        if fh.status == 304:
#            print "Header info not modified"
            return None

    # hook in progress callbacks
    lmtime = get_modified(fh)
    if not lmtime:
        lmtime = time.gmtime(time.time())

    #buffer = fh.read()
    buffer = readFDBuf(fh, progressCallback) 
    fh.close()

    return (buffer, lmtime)


# need to add callbacks at some point
def fetchUrlAndWriteFD(url, writefd, progressCallback=None, msgCallback=None,
             lastModified=None, agent=None):
    fh = open_resource(url, modified=lastModified,
                                    agent = agent)

    if hasattr(fh,'status'):
        if fh.status == 304:
#            print "Header info not modified"
            return None

    # hook in progress callbacks
    lmtime = get_modified(fh)
    if not lmtime:
        lmtime = time.gmtime(time.time())

    #buffer = fh.read()
    ret =  readFDBufWriteFD(fh, writefd, progressCallback) 
    fh.close()

    return (lmtime)

#    return (buffer, lmtime)

def main():
    fh = open_resource("http://www.japanairband.com/sdfsdfasdferwregsdfg/",
                       agent = "foobar")
    print fh

    if hasattr(fh, 'status'):
        print "status: %s" % fh.status
    else:
        print "no status"


if __name__ == "__main__":
    main()
    
