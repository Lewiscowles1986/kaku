# -*- coding: utf-8 -*-
"""
:copyright: (c) 2016 by Mike Taylor
:license: CC0 1.0 Universal, see LICENSE for more details.
"""

import os
import re
import datetime

from unidecode import unidecode

import pytz

from flask import current_app

from kaku.tools import kakuEvent


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
def createSlug(title, delim=u'-'):
    result = []
    for word in _punct_re.split(title.lower()):
        result.extend(unidecode(word).split())
    return unicode(delim.join(result))

# TODO: figure out how to make determination of the title configurable
def determineTitle(mpData, timestamp):
    summary = ''
    if 'summary' in mpData and mpData['summary'] is not None:
        summary = mpData['summary']
    if len(summary) == 0:
        if 'content' in mpData and mpData['content'] is not None:
            summary = mpData['content'].split('\n')[0]
    if len(summary) == 0:
        title = 'micropub post %s' % timestamp.strftime('%H%M%S')
    else:
        title = summary
    return title

# TODO: figure out how to make the calculation of the location configurable
def generateLocation(timestamp, slug):
    baseroute = current_app.config['BASEROUTE']
    year      = str(timestamp.year)
    doy       = timestamp.strftime('%j')
    location  = os.path.join(baseroute, year, doy, slug)
    return location

def micropub(event, mpData):
    if event == 'POST':
        properties = mpData['properties']
        if 'h' in properties and properties['h'] is not None:
            if properties['h'].lower() not in ('entry',):
                return ('Micropub CREATE requires a valid action parameter', 400, {})
            elif properties['content'] is None:
                return ('Micropub CREATE requires a content property', 400, {})
            else:
                try:
                    utcdate   = datetime.datetime.utcnow()
                    tzLocal   = pytz.timezone('America/New_York')
                    timestamp = tzLocal.localize(utcdate, is_dst=None)
                    title     = determineTitle(properties, timestamp)
                    slug      = createSlug(title)
                    location  = generateLocation(timestamp, slug)
                    if os.path.exists(os.path.join(current_app.config['SITE_CONTENT'], '%s.md' % location)):
                        return ('Micropub CREATE failed, location already exists', 406)
                    else:
                        data = { 'slug':      slug,
                                 'title':     title,
                                 'location':  location,
                                 'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                 'micropub':  properties,
                               }
                        current_app.logger.info('micropub create event for [%s]' % slug)
                        kakuEvent('post', 'create', data)
                        return ('Micropub CREATE successful for %s' % location, 202, {'Location': location})
                except:
                    current_app.logger.exception('Exception during micropub handling')
                    return ('Unable to process Micropub request', 400, {})
        elif 'mp-action' in properties and properties['mp-action'] is not None:
            action = properties['mp-action'].lower()
            if action in ('delete', 'undelete'):
                if 'url' in properties and properties['url'] is not None:
                    url = properties['url']
                    try:
                        data = { 'url': url }
                        kakuEvent('post', action, data)
                        return ('Micropub %s successful for %s' % (action, url), 202, {'Location': url})
                    except:
                        current_app.logger.exception('Exception during micropub handling')
                        return ('Unable to process Micropub request', 400, {})
                else:
                    return ('Micropub %s request requires a URL' % action, 400, {})
        else:
            return ('Invalid Micropub CREATE request', 400, {})
    else:
        return ('Unable to process Micropub %s' % data['event'], 400, {})
