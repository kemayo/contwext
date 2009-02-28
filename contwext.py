#!/usr/bin/python

import urllib2
import gzip
import sys
import re
from datetime import datetime, timedelta
from StringIO import StringIO

# python 2.6 has json included, otherwise try to get simplejson if it's available
try:
    import json
except ImportError:
    import simplejson as json

__author__ = 'David Lynch (kemayo at gmail dot com)'
__version__ = '0.1'
__copyright__ = 'Copyright (c) 2009 David Lynch'
__license__ = 'New BSD License'

USER_AGENT = 'contwext/%s' % __version__
TWITTER_URL = 'http://twitter.com'

cache = {}

def twitter(method, **kwargs):
    params = '&'.join(["%s=%s" % (k,v) for k,v in kwargs.items()])
    url = "%s/%s.json?suppress_response_codes&%s" % (TWITTER_URL, method, params)
    if url in cache:
        return cache[url]
    response = _fetch(url)
    decoded_response = json.loads(response.read())
    cache[url] = decoded_response
    return decoded_response

def fetch_statuses(id, time, limit=5):
    """Fetches statuses by a user until time"""
    complete = False
    page = 1
    all = []
    while not complete:
        if page > limit:
            # just give up if this is taking too long
            break
        tweets = twitter("statuses/user_timeline", id=id, page=page)
        if 'error' in tweets:
            # probably a protected user
            break
        for tweet in tweets:
            all.append(tweet)
            created_at = twitter_datetime(tweet['created_at'])
            if created_at < time:
                complete = True
                break
        page = page + 1
    return all

def fetch_status(id):
    tweet = twitter('statuses/show/%s' % id)
    if 'error' in tweet:
        return False
    return tweet

def fetch_conversation(id, time, guess=True, guess_threshold=timedelta(minutes=15)):
    all = []
    my_tweets = fetch_statuses(id, time) # 1 day ago
    for tweet in my_tweets:
        all.append(tweet)
        if tweet['in_reply_to_status_id']:
            # they responded by pressing the reply button
            reply_tweet = fetch_status(tweet['in_reply_to_status_id'])
            all.append(reply_tweet)
        elif guess and tweet['in_reply_to_screen_name']:
            # they just typed @foo in; try to guess at the tweet it's responding to.
            tweet_time = twitter_datetime(tweet['created_at'])
            their_tweets = fetch_statuses(tweet['in_reply_to_screen_name'], tweet_time - guess_threshold)
            for t in their_tweets:
                if twitter_datetime(t['created_at']) < tweet_time:
                    all.append(t)
                    break
    return all

def format_status(tweet):
    return "[%s] &lt;%s&gt; %s %s" % (format_time(tweet['created_at']), format_user(tweet['user']), format_status_text(tweet['text']), link_to_status(tweet))

def format_status_text(text):
    text = re.sub(r'((?:http.?||ftp)://[\S]+)', r'<a href="\1">\1</a>', text)
    text = re.sub(r'@([\S]{1,15})', r'<a href="%s/\1">@\1</a>' % TWITTER_URL, text)
    return text

def format_user(user):
    return '<a href="%s/%s">%s</a>' % (TWITTER_URL, user['screen_name'], user['name'])

def format_time(time, format="%H:%M"):
    return twitter_datetime(time).strftime(format)

def link_to_status(tweet, text="#"):
    return '<a href="%s/%s/statuses/%s">%s</a>' % (TWITTER_URL, tweet['user']['screen_name'], tweet['id'], text)

def twitter_datetime(s):
    # twitter gives times similar to: 'Fri Feb 27 07:43:24 +0000 2009'
    return datetime.strptime(s, '%a %b %d %H:%M:%S +0000 %Y')

def _fetch(url):
    """A generic URL-fetcher, which handles gzipped content, returns a file-like object"""
    request = urllib2.Request(url)
    request.add_header('Accept-encoding', 'gzip')
    request.add_header('User-agent', USER_AGENT)
    f = urllib2.urlopen(request)
    data = StringIO(f.read())
    f.close()
    if f.headers.get('content-encoding', '') == 'gzip':
        data = gzip.GzipFile(fileobj=data)
    return data

if __name__ == "__main__":
    conversation = fetch_conversation('kemayo', datetime.now() - timedelta(days=1))
    for tweet in conversation:
        print format_status(tweet)

