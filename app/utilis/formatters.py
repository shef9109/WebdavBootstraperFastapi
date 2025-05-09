import re
import sys
# import urllib.request, urllib.parse, urllib.error, urllib.parse
from time import timezone, strftime, localtime, gmtime


def parse_int(s: str, default: int = 0) -> int:
  try:
    i = int(s)
  except ValueError:
    i = default
  return i

def unixdate2iso8601(d):
  tz = timezone / 3600
  tz = '%+03d' % tz
  return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
  return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))


class Tag:
  def __init__(self, name, attrs, data='', parser=None):
    self.d = {}
    self.name = name
    self.attrs = attrs
    if type(self.attrs) == type(''):
      self.attrs = splitattrs(self.attrs)
    for a in self.attrs:
      if a.startswith('xmlns'):
        nsname = a[6:]
        parser.namespaces[nsname] = self.attrs[a]
    self.rawname = self.name

    p = name.find(':')
    if p > 0:
      nsname = name[0:p]
      if nsname in parser.namespaces:
        self.ns = parser.namespaces[nsname]
        self.name = self.rawname[p + 1:]
    else:
      self.ns = ''
    self.data = data

  # Emulate dictionary d
  def __len__(self):
    return len(self.d)

  def __getitem__(self, key):
    return self.d[key]

  def __setitem__(self, key, value):
    self.d[key] = value

  def __delitem__(self, key):
    del self.d[key]

  def __iter__(self):
    return iter(self.d.keys())

  def __contains__(self, key):
    return key in self.d

  def __str__(self):
    """Returns unicode semi human-readable representation of the structure"""
    if self.attrs:
      s = '<%s %s> %s ' % (self.name, self.attrs, self.data)
    else:
      s = '<%s> %s ' % (self.name, self.data)

    for k in self.d:
      if type(self.d[k]) == type(self):
        s += '|%s: %s|' % (k, str(self.d[k]))
      else:
        s += '|' + ','.join([str(x) for x in self.d[k]]) + '|'
    return s

  def addChild(self, tag):
    """Adds a child to self. tag must be instance of Tag"""
    if tag.name in self.d:
      if type(self.d[tag.name]) == type(self):  # If there are multiple sibiling tags with same name, form a list :)
        self.d[tag.name] = [self.d[tag.name]]
      self.d[tag.name].append(tag)
    else:
      self.d[tag.name] = tag
    return tag


class XMLDict_Parser:
  def __init__(self, xml):
    self.xml = xml
    self.p = 0
    self.encoding = sys.getdefaultencoding()
    self.namespaces = {}

  def getnexttag(self):
    ptag = self.xml.find('<', self.p)
    if ptag < 0:
      return None, None, self.xml[self.p:].strip()
    data = self.xml[self.p:ptag].strip()
    self.p = ptag
    self.tagbegin = ptag
    p2 = self.xml.find('>', self.p + 1)
    if p2 < 0:
      raise "Malformed XML - unclosed tag?"
    tag = self.xml[ptag + 1:p2]
    self.p = p2 + 1
    self.tagend = p2 + 1
    ps = tag.find(' ')
    ### Change By LCJ @ 2017/9/7 from  [ if ps > 0: ]  ###
    ### for IOS Coda Webdav support ###
    if ps > 0 and tag[-1] != '/':
      tag, attrs = tag.split(' ', 1)
    else:
      attrs = ''
    return tag, attrs, data

  def builddict(self):
    """Builds a nested-dictionary-like structure from the xml. This method
    picks up tags on the main level and calls processTag() for nested tags."""
    d = Tag('<root>', '')
    while True:
      tag, attrs, data = self.getnexttag()
      if data != '':  # data is actually that between the last tag and this one
        sys.stderr.write("Warning: inline data between tags?!\n")
      if not tag:
        break
      if tag[-1] == '/':  # an 'empty' tag (e.g. <empty/>)
        d.addChild(Tag(tag[:-1], attrs, parser=self))
        continue
      elif tag[0] == '?':  # special tag
        t = d.addChild(Tag(tag, attrs, parser=self))
        if tag == '?xml' and 'encoding' in t.attrs:
          self.encoding = t.attrs['encoding']
      else:
        try:
          self.processTag(d.addChild(Tag(tag, attrs, parser=self)))
        except:
          sys.stderr.write("Error processing tag %s\n" % tag)
    d.encoding = self.encoding
    return d

  def processTag(self, dtag):
    """Process single tag's data"""
    until = '/' + dtag.rawname
    while True:
      tag, attrs, data = self.getnexttag()
      if data:
        dtag.data += data
      if tag == None:
        sys.stderr.write("Unterminated tag '" + dtag.rawname + "'?\n")
        break
      if tag == until:
        break
      if tag[-1] == '/':
        dtag.addChild(Tag(tag[:-1], attrs, parser=self))
        continue
      self.processTag(dtag.addChild(Tag(tag, attrs, parser=self)))


def splitattrs(att):
  """Extracts name="value" pairs from string; returns them as dictionary"""
  d = {}
  for m in re.findall('([a-zA-Z_][a-zA-Z_:0-9]*?)="(.+?)"', att):
    d[m[0]] = m[1]
  return d


def builddict(xml):
  """Wrapper function for straightforward parsing"""
  p = XMLDict_Parser(xml)
  return p.builddict()
