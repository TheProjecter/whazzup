
import time, vectors, operator, string, math, formatmodules, HTMLParser, rsslib, codecs, traceback, cgi, chew, datetime
from xml.sax import SAXException

# --- Constants

START_VOTES = 5
TIME_TO_WAIT = 3600 * 3 # 3 hours

# --- Utilities

def nice_time(secs):
    if secs > 86400:
        return "%s days" % (secs / 86400)
    if secs > 3600:
        if secs < (3600 * 3):
            return "%s hours %s mins" % (secs / 3600, (secs % 3600) / 60)
        else:
            return "%s hours" % (secs / 3600)
    if secs > 60:
        return "%s minutes" % (secs / 60)
    return "%s seconds" % secs

def html2text(str):
    str = string.replace(str, "&lt;", "<")
    str = string.replace(str, "&gt;", ">")
    str = string.replace(str, "&amp;", "&")
    ext = formatmodules.HTMLExtractor()
    try:
        ext.feed(str)
    except HTMLParser.HTMLParseError:
        pass # it's OK
    return ext.get_text()

def sort(list, keyfunc):
    list = map(lambda x, y=keyfunc: (y(x), x), list)
    list.sort()
    return map(lambda x: x[1], list)

def escape(str): # HTML escape
    return cgi.escape(str)

def attrescape(str): # HTML attribute escape
    return string.replace(escape(str), '"', '&quot;')

def compute_bayes(probs):
    product = reduce(operator.mul, probs)
    lastpart = reduce(operator.mul, map(lambda x: 1-x, probs))
    if product + lastpart == 0:
        return 0 # happens rarely, but happens
    else:
        return product / (product + lastpart)

def compute_average(probs):
    sum = reduce(operator.add, probs)
    return sum / float(len(probs))

def parse_date(datestring):
    if datestring:
        formats = [("%a, %d %b %Y %H:%M:%S", 24),
                   ("%Y-%m-%dT%H:%M:%S", 19),
                   ("%a, %d %b %Y %H:%M", 22),
                   ("%Y-%m-%d", 10),

                   #Sun Jan 16 15:55:53 UTC 2011
                   ("%a %b %d %H:%M:%S +0000 %Y", 30),

                   #Sun, 16 January 2011 07:13:33
                   ("%a, %d %B %Y %H:%M:%S", 29)]
        for (format, l) in formats:
            try:
                return datetime.datetime.strptime(datestring[ : l], format)
            except ValueError:
                pass

        print "CAN'T PARSE:", repr(datestring)

    return datetime.utcnow()

def toseconds(timestamp):
    return time.mktime(timestamp.timetuple())

def calculate_points(prob, postdate):
    age = time.time() - toseconds(postdate)
    if age < 0:
        age = 3600
    return (prob * 1000.0) / math.log(age)

# --- Controller

class Controller:
    "A mediator between the UI and the backend."

    def add_feed(self, url):
        raise NotImplementedError()

    def in_appengine(self):
        return False

    def get_queue_delay(self):
        return 0

    def recalculate_all_posts(self):
        pass

# --- Model

class Database:

    def __init__(self):
        pass

    def record_word_vote(self, word, vote):
        self._get_word_db().record_vote(word, vote)

    def record_author_vote(self, author, vote):
        self._get_author_db().record_vote(author, vote)

    def record_site_vote(self, site, vote):
        self._get_site_db().record_vote(site, vote)

    def get_word_ratio(self, word):
        worddb = self._get_word_db()
        return worddb.get_word_ratio(word)
    
    def get_author_ratio(self, word):
        authordb = self._get_author_db()
        return authordb.get_word_ratio(word)
        
    # backend-specific

    def get_feeds(self):
        raise NotImplementedError()
    
    def get_item_count(self):
        raise NotImplementedError()
        
    def get_item_range(self, low, high):
        raise NotImplementedError()

    def get_item_by_id(self, id):
        raise NotImplementedError() # do we need this? should it stay?

    def get_rated_post_by_id(self, id, username):
        raise NotImplementedError()
    
    def seen_link(self, link):
        "Marks the link as seen."
        raise NotImplementedError()

    def is_link_seen(self, link):
        "Returns true if the link has been seen."
        raise NotImplementedError()

    def get_no_of_item(self, item):
        raise NotImplementedError()
    
    def commit(self):
        raise NotImplementedError()

    def get_vote_stats(self):
        "Returns a tuple (upvotes, downvotes)."
        raise NotImplementedError()
    
    def _get_word_db(self):
        raise NotImplementedError()

    def _get_author_db(self):
        raise NotImplementedError()

    def _get_site_db(self):
        raise NotImplementedError()
    
class Feed:

    def get_local_id(self):
        "String: internal ID of the feed."
        raise NotImplementedError()

    def get_title(self):
        raise NotImplementedError()

    def get_url(self):
        "String: the URL of the XML feed."
        raise NotImplementedError()
    
    def get_link(self):
        "String: the URL of the feed's home page."
        raise NotImplementedError()

    def get_error(self):
        """String: the text of the error message received when last
        attempting to load this feed."""
        raise NotImplementedError()

    def get_time_to_wait(self):
        "Seconds to wait between each time we poll the feed."
        raise NotImplementedError()
    
    def time_since_last_read(self):
        "Seconds since last read."
        raise NotImplementedError()
    
    def get_item_count(self):
        raise NotImplementedError()

    def get_ratio(self):
        raise NotImplementedError()

    def get_items(self):
        raise NotImplementedError()

    def record_vote(self, vote):
        raise NotImplementedError()
            
    def is_being_read(self):
        raise NotImplementedError()

    def is_subscribed(self):
        raise NotImplementedError()

    def get_subscribers(self):
        raise NotImplementedError()
    
    # shared code

    def nice_time_since_last_read(self):
        return nice_time(int(self.time_since_last_read()))
    
class Post:

    def __init__(self):
        self._date = None
    
    def get_local_id(self):
        raise NotImplementedError()

    def get_title(self):
        raise NotImplementedError()

    def get_link(self):
        raise NotImplementedError()
    
    def get_description(self):
        raise NotImplementedError()

    def get_date(self):
        "Returns a datetime object representing the publication date."
        if not self._date:
            self._date = parse_date(self.get_pubdate())
        return self._date
    
    def get_pubdate(self):
        raise NotImplementedError()

    def get_age(self):
        age = time.time() - toseconds(self.get_date())
        if age < 0:
            age = 3600
        return age

    def get_site(self):
        raise NotImplementedError()

    def get_guid(self):
        raise NotImplementedError()

    def get_author(self):
        raise NotImplementedError()
    
    # shared code

    def nice_age(self):
        return nice_time(int(self.get_age()))
    
    def get_author_vector(self):
        return vectors.text_to_vector(html2text(self.get_author() or ""))

    def get_url_tokens(self):
        tokens = self.get_link().split("/")
        end = -1
        if not tokens[-1]: # if url of form http://site/foo/bar/
            end = -2
        tokens = tokens[2 : end]
        return string.join(["url:" + t for t in tokens if chew.acceptable_term(t)])

    def get_word_tokens(self):
        probs = []
        for (word, count) in self.get_vector().get_pairs():
            for ix in range(count):
                ratio = feeddb.get_word_ratio(word)
                probs.append("%s : %s" % (escape(word), ratio))
        return ", ".join(probs)

    def get_vector(self):
        html = (self.get_title() or "") + " " + (self.get_description() or "")
        text = html2text(html) + " " + self.get_url_tokens()
        vector = vectors.text_to_vector(text, {}, None, 1)
        return vector

class Subscription:

    def get_feed(self):
        raise NotImplementedError()

    def get_user(self):
        raise NotImplementedError()

    def get_ratio(self):
        raise NotImplementedError()
    
class RatedPost:

    def __init__(self, username, post, subscription, points = None):
        self._post = post
        self._subscription = subscription
        self._username = username
        self._points = points

    def get_post(self):
        return self._post

    def get_subscription(self):
        return self._subscription
        
    def get_points(self):
        return self._points

    def set_points(self, points):
        self._points = points

    def is_seen(self):
        return feeddb.is_link_seen(self) # FIXME: not sure about this

    def get_word_probability(self):
        probs = []
        for (word, count) in self._post.get_vector().get_pairs():
            for ix in range(count):
                ratio = feeddb.get_word_ratio(word)
                probs.append(ratio)

        try:
            if not probs:
                return 0.5 # not sure how this could happen, though
            else:
                return compute_bayes(probs)
        except ZeroDivisionError, e:
            print "ZDE:", self._post.get_title().encode("utf-8"), probs
    
    def get_overall_probability(self):
        word_prob = self.get_word_probability()
        site_prob = self.get_site_probability()
        author_prob = self.get_author_probability()
        return compute_bayes([word_prob, site_prob, author_prob])
    
    def get_site_probability(self):
        return self.get_subscription().get_ratio()
        
    def get_author_probability(self):
        author = self._post.get_author()
        if author:
            author = string.strip(string.lower(author))
            return feeddb.get_author_ratio(author)
        else:
            return 0.5
        
    def recalculate(self):
        try:
            prob = self.get_overall_probability()
            self._points = calculate_points(prob, self._post.get_date())
        except ZeroDivisionError, e:
            #print "--------------------------------------------------"
            print self._post.get_title().encode("utf-8")
            self._points = 0

    def record_vote(self, vote):
        feeddb.remove_item(self)

        if vote != "read":
            for (word, count) in self._post.get_vector().get_pairs():
                for i in range(count):
                    feeddb.record_word_vote(word, vote)
            author = self._post.get_author()
            if author:
                author = string.strip(string.lower(author)) # move into feeddb
                feeddb.record_author_vote(author, vote)

            feeddb.record_site_vote(self._post.get_site().get_link(), vote)
            feeddb.commit()
            
        feeddb.seen_link(self)
        # the UI takes care of queueing a recalculation task

# --- Word database

# FIXME: this needs to be properly generalized

class WordDatabase:

    def __init__(self, words):
        self._words = words # a dict, of some kind, possibly a dbm

    def get_word_ratio(self, word):
        (good, bad) = self._get_object(word)
        return float(good + START_VOTES) / (good + bad + START_VOTES * 2)

    def get_word_stats(self, word):
        return self._get_object(word)

    def record_vote(self, theword, vote):
        (good, bad) = self._get_object(theword)
        if vote == "up":
            good += 1
        else:
            bad += 1
        self._put_object(theword, (good, bad))

    def change_word(self, oldword, newword):
        ratio = self.get_word_ratio(oldword)
        del self._words[oldword.encode("utf-8")]
        self._put_object(theword, ratio)

    def _get_object(self, key):
        return self._words.get(key, (0, 0))

    def _put_object(self, key, ratio):
        self._words[key] = ratio

    def close(self):
        raise NotImplementedError()
