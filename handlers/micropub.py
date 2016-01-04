# -*- coding: utf-8 -*-
"""
:copyright: (c) 2015-2016 by Mike Taylor
:license: MIT, see LICENSE for more details.

Micropub handler
"""

import os
import re
import pytz
import datetime
import traceback

from bearlib.config import Config
from dateutil.parser import parse
from unidecode import unidecode


def buildTemplateContext(cfg):
    result = {}
    for key in ('baseurl', 'title', 'meta'):
        if key in cfg:
            value = cfg[key]
        else:
            value = ''
        result[key] = value
    return result

# from http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
def createSlug(text, delim=u'-'):
    result = []
    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word).split())
    return unicode(delim.join(result))

def createPath(path, log):
    result = True
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        log.exception(exc)
        if os.path.isdir(path):
            pass
        else:
            result = False
    return result

_article_file = """Title:   %(title)s
Date:    %(published)s
Tags:    %(tags)s
Author:  %(author)s
Slug:    %(slug)s
Summary: %(title)s

%(content)s
"""

def createBookmark(data, db, log, cfg):
    if 'published' in data and data['published'] is not None:
        d = parse(data['published'])
    else:
        d = datetime.datetime.utcnow()
    tzLocal   = pytz.timezone('America/New_York')
    timestamp = tzLocal.localize(d, is_dst=None)
    slug      = 'bookmarks'
    location  = os.path.join(cfg.contentpath, str(timestamp.year), timestamp.strftime('%j'), slug)
    task      = { 'action':    'create',
                  'type':      'bookmark',
                  'slug':      slug,
                  'url':       data['like-of'],
                  'category':  data['category'],
                  'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                  'location':  location
                }
    db.rpush('micropub-tasks', task)
    return location, 202

def createArticle(data, db, log, cfg):
    if 'published' in data and data['published'] is not None:
        d = parse(data['published'])
    else:
        d = datetime.datetime.utcnow()
    if 'title' in data:
        title = data['title']
    else:
        title = data['content'].split('\n')[0],
    tzLocal   = pytz.timezone('America/New_York')
    timestamp = tzLocal.localize(d, is_dst=None)
    slug      = createSlug(title)
    location  = os.path.join(cfg.contentpath, str(timestamp.year), timestamp.strftime('%j'), slug)
    task      = { 'action':    'create',
                  'type':      'article',
                  'slug':      slug,
                  'title':     title,
                  'content':   data['content'],
                  'category':  data['category'],
                  'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                  'location':  location
                }
    db.rpush('micropub-tasks', task)
    return location, 202

def createNote(data, db, log, cfg):
    if 'published' in data and data['published'] is not None:
        d = parse(data['published'])
    else:
        d = datetime.datetime.utcnow()
    if 'title' in data:
        title = data['title']
    else:
        title = data['content'].split('\n')[0],
    tzLocal   = pytz.timezone('America/New_York')
    timestamp = tzLocal.localize(d, is_dst=None)
    slug      = createSlug(title)
    location  = os.path.join(cfg.contentpath, str(timestamp.year), timestamp.strftime('%j'), slug)
    task      = { 'action':    'create',
                  'type':      'note',
                  'slug':      slug,
                  'title':     title,
                  'content':   data['content'],
                  'category':  data['category'],
                  'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                  'location':  location
                }
    db.rpush('micropub-tasks', task)
    return location, 202

def micropub(data, db, log, siteConfigFilename):
    # yes, I know, it's a module global...
    cfg = Config()
    if os.path.exists(siteConfigFilename):
        cfg.fromJson(siteConfigFilename)
    try:
        if data['event'] == 'create':
            if 'h' in data:
                if data['h'].lower() not in ('entry',):
                    return ('Micropub CREATE requires a valid action parameter', 400, {})
                else:
                    try:
                        utcdate   = datetime.datetime.utcnow()
                        tzLocal   = pytz.timezone('America/New_York')
                        timestamp = tzLocal.localize(utcdate, is_dst=None)

                        if 'content' in data and data['content'] is not None:
                            title = data['content'].split('\n')[0]
                        else:
                            title = 'event-%s' % timestamp.strftime('%H%M%S')
                        slug     = createSlug(title)
                        location = os.path.join(data['basepath'], str(timestamp.year), timestamp.strftime('%j'), slug)
                        event    = { 'type':     'micropub',
                                     'slug':      slug,
                                     'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                     'location':  '%s%s' % (data['baseurl'], location),
                                     'payload':   {
                                         'micropub': data,
                                         'siteConfig': cfg,
                                     },
                                   }
                        db.rpush('kaku-events', event)
                        return ('Micropub CREATE successful for %s' % location, 202, {'Location': location})
                    except Exception:
                        log.exception('Exception during micropub handling')

                    return ('Micropub CREATE failed', 500, {})
            else:
                return ('Invalid Micropub CREATE request', 400, {})
        else:
            return ('Unable to process Micropub %s' % data['event'], 400, {})
    except:
        pass

    # should only get here if an exception has occurred
    traceback.print_exc()
    return ('Unable to process Micropub', 400, {})
