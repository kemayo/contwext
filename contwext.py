#!/usr/bin/python

import urllib2
import gzip
import sys
import re
import rfc822
import calendar
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

USER_AGENT = 'contwext/%s +http://github.com/kemayo/contwext/tree/master' % __version__
TWITTER_URL = 'http://twitter.com'

cache = {}
status_cache = {}

class Status(object):
    """Represent a single twitter status update"""
    def __init__(self, tweet):
        self.id = tweet['id']
        self.text = tweet['text']
        self.user = User(tweet['user'])
        self.created_at = twitter_datetime(tweet['created_at'])
        self.in_reply_to_screen_name = tweet['in_reply_to_screen_name']
        self.in_reply_to_user_id = tweet['in_reply_to_user_id']
        self.in_reply_to_status_id = tweet['in_reply_to_status_id']
        self.extra = tweet
    
    def __eq__(self, other):
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return "%s: %s" % (self.user, self.text)

    def __cmp__(self, other):
        if hasattr(other, "created_at"):
            return cmp(self.created_at, other.created_at)
        return cmp(self.id, other)

    def html(self, format = "[%s] &lt;%s&gt; %s %s"):
        # linkify the main text
        text = re.sub(r'((?:http.?||ftp)://[\S]+)', r'<a href="\1">\1</a>', self.text)
        text = re.sub(r'@([\S]{1,15})', r'<a href="%s/\1">@\1</a>' % TWITTER_URL, text)
        text = re.sub(r'(?<=\s)#(\S*)', r'<a href="%s/search?q=\1">#\1</a>', text)
        time = self.created_at.strftime("%H:%M")

        
        return format % (time, self.user.html(), text, self.link())
    
    def link(self, text = "#"):
        return '<a href="%s">%s</a>' % (self.url(), text)

    def url(self):
        return '%s/%s/statuses/%s' % (TWITTER_URL, self.user.screen_name, self.id)

class User(object):
    """Represent a twitter user"""
    def __init__(self, user):
        self.id = user['id']
        self.screen_name = user['screen_name']
        self.name = user['name']
        self.extra = user

    def __eq__(self, other):
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.screen_name

    def html(self, format = '%s'):
        return format % self.link()
    
    def link(self, text = None):
        return '<a href="%s" title="%s">%s</a>' % (self.url(), self.name, text or self.screen_name)

    def url(self):
        return '%s/%s' % (TWITTER_URL, self.screen_name)

def twitter_api(method, **kwargs):
    """Fetches the result of a twitter API method"""
    params = '&'.join(["%s=%s" % (k,v) for k,v in kwargs.items()])
    url = "%s/%s.json?suppress_response_codes&%s" % (TWITTER_URL, method, params)
    if url in cache:
        return cache[url]
    response = _fetch(url)
    decoded_response = json.loads(response.read())
    cache[url] = decoded_response
    return decoded_response

def fetch_statuses(id, time, limit=10, method="statuses/user_timeline"):
    """Fetches statuses by a user until time"""
    complete = False
    page = 1
    all = []
    while not complete:
        if page > limit:
            # just give up if this is taking too long
            break
        tweets = twitter_api(method, id=id, page=page)
        if 'error' in tweets:
            # probably a protected user
            break
        for tweet in tweets:
            tweet = Status(tweet)
            status_cache[tweet.id] = tweet
            if tweet.created_at < time:
                complete = True
                break
            all.append(tweet)
        page = page + 1
    return all

def fetch_status(id):
    """Fetch a single twitter update by id"""
    if id in status_cache:
        return status_cache[id]
    tweet = twitter_api('statuses/show/%s' % id)
    if 'error' in tweet:
        return False
    tweet = Status(tweet)
    status_cache[id] = tweet
    return tweet

def fetch_conversation(id, time, guess=True, guess_threshold=timedelta(minutes=15), reply_threshold=timedelta(hours=6)):
    """Attempt to fetch all tweets and their involved conversations for a given user, within a given time period"""
    all = set()
    my_tweets = fetch_statuses(id, time) # 1 day ago
    for tweet in my_tweets:
        all.add(tweet)
        if tweet.in_reply_to_status_id:
            # Responded by pressing the reply button. THIS MAKES MY LIFE SO MUCH EASIER!
            reply_tweet = fetch_status(tweet.in_reply_to_status_id)
            if reply_tweet:
                all.add(reply_tweet)
        elif guess and tweet.in_reply_to_screen_name:
            # Just typed @foo in; try to guess at the tweet it's responding to.
            # This is very inexact, unfortunately. It tries to fetch a tweet within reply_threshold
            # of this tweet, which is in reply to this user -- this should work best for a case of back-and-forth
            # tweeting. Otherwise it checkes whether the most recent tweet of the replied-to user is within
            # reply_threshold of this tweet, and assumes it's the one being replied to.
            # This is an algorithm that could use improvement, but it works for my low-activity account.
            their_tweets = fetch_statuses(tweet.in_reply_to_screen_name, tweet.created_at - max(guess_threshold, reply_threshold))
            candidate = False
            for t in their_tweets:
                if t.created_at < tweet.created_at:
                    if t.created_at > (tweet.created_at - reply_threshold) and t.in_reply_to_screen_name == id:
                        candidate = t
                        break
            if not candidate and their_tweets[0].created_at > (tweet.created_at - guess_threshold):
                    candidate = their_tweets[0]
            if candidate:
                all.add(candidate)
    all = list(all)
    all.sort()
    return all

def twitter_datetime(s):
    """Turn twitter's rfc822 created_at times into a datetime in the local timezone"""
    # twitter gives times similar to: 'Fri Feb 27 07:43:24 +0000 2009'
    # Who would have thought that converting these to the current timezone would be such a bitch?
    return datetime.fromtimestamp(calendar.timegm(rfc822.parsedate(s)))

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
    id = 'kemayo'
    conversation = fetch_conversation(id, datetime.now() - timedelta(days=2), guess_threshold = timedelta(hours=1))
    for tweet in conversation:
        if tweet.user.screen_name == id:
            print tweet
        else:
            print '***', tweet

