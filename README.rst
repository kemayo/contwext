========
Contwext
========

Intro
-----

Contwext is a simple python module that pulls a user's feed from
Twitter, and tries to fill in the context for all those @replies.

It does this with a sequence of criteria:

1. If twitter provides in_reply_to_status_id, that's definitely
   it.
2. If the @replied to user did an @reply to the original user
   within a configurable time, that's probably it.
3. If the @replied to user posted anything within a (shorter)
   configurable time, that's possibly it.

This is inexact, but works okay for non-prolific tweeters. I'd
welcome suggestions for improvements to this.

Usage
-----

>>> import contwext
>>> conversation = contwext.fetch_conversation('kemayo', datetime.now() - timedelta(days = 1))
>>> for tweet in conversation: print tweet
kemayo: Strongly tempted to write a contextual retweeter for LJ, which would include the tweets you @replied to.
*** miksago: @kemayo LiveJournal.. wasn't that.. sorta deceased?
kemayo: @miksago One is tied to it by community.
*** gamoid: @kemayo If it worked better than LoudTwitter, I'd use it.

Tweets are represented as objects of the ``contwext.Status`` class. They
have useful attributes like ``text``, ``user``, and ``created_at``.

Users are represented as objects of the ``contwext.User`` class. They have
useful attributes like ``screen_name`` and ``name``.

If http://github.com/kemayo/longurl is present it'll be used to expand URLs in
status updates when the Status.html() method is called. I might rearrange this
in the future...

Sample
------

Included is ``contwext_journal.py``, which will post a twitter user's
last day of conversation to livejournal.

To run it you need ljpy: http://code.google.com/p/ljpy

Rename contwext_journal.ini.default to contwext_journal.ini and enter your
information.

