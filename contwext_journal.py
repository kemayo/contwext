#!/usr/bin/python

import ConfigParser
import sys

from datetime import datetime, timedelta

import contwext
import lj

def post(username, password, event):
    server = lj.LJServer('Python-lj.py+contwext/0.1.0', 'http://github.com/kemayo/contwext/tree/master; kemayo@gmail.com')
    try:
        login = server.login(username, password)
    except lj.LJException, e:
        sys.exit(e)

    server.postevent(event, subject="Contwextual information")

def format_conversation(conversation, owner):
    output = ['<ul>']
    for tweet in conversation:
        output.append('<li>')
        if tweet.user.screen_name != owner:
            output.append('<i>')
        output.append(tweet.html())
        if tweet.user.screen_name != owner:
            output.append('</i>')
        output.append('</li>')
    output.append('</ul><p>Posted with <a href="http://github.com/kemayo/contwext/tree/master">Contwext</a></p>')
    return ''.join(output)

if __name__ == "__main__":
    config = ConfigParser.SafeConfigParser()
    config.read('contwext_journal.ini')
    twitter_user = config.get('twitter', 'username')
    twitter_days = int(config.get('twitter', 'days'))
    lj_user = config.get('lj', 'username')
    lj_pass = config.get('lj', 'password')

    conversation = contwext.fetch_conversation(twitter_user, datetime.now() - timedelta(days=twitter_days))
    if len(conversation) == 0:
        sys.exit("Nothing to post.")
    
    postinfo = post(lj_user, lj_pass, format_conversation(conversation, twitter_user))
    print "Posted %d tweets" % len(conversation)

