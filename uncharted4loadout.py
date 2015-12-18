import datetime
import praw
import time
import re
import csv
import os

__author__ = '/u/spookyyz'
__version__ = '0.2'
user_agent = 'Uncharted 4 Loadout Poster by /u/spookyyz'
bot_signature = "\r\n\r\n^(_Uncharted 4 Loadout Bot v%s created by /u/spookyyz ) ^|| ^(Feel free to message me with any ideas or problems_)" % __version__

###########Global Vars
SUBREDDIT = 'uncharted'
PATTERN = re.compile('http:\/\/loadout\.unchartedmultiplayer\.com\/?\?q\=[\d,.]+')
WAIT_TIME = 30
SLEEP_TIME = 10
DEVELOPER = False #True to print output instead of post
START_TIME = time.time() #new var to monitor time of startup so posts prior to that time can be ignored. (in Unix)
###########

########## CSV processing
try:
    with open('Uncharted4items.csv', 'rb') as f:
        loadout_data = []
        reader = csv.reader(f)
        for row in reader:
            loadout_data.append(row)
except Exception, e:
    print "ERROR(@csv): " + str(e)
    exit()
print "SUCCESS(@csv): " + str(len(loadout_data)) + " items loaded from " + f.name
########## end of CSV



#print ("Success: Logged in.")

class uncharted4_bot(object):
    """
    This little fella is gonna poll the /r/uncharted4multiplayer sub for any loadouts links posted from
    loadout.unchartedmultiplayer.com and post the items in that loadout!
    """

    def __init__(self):
        self.cache = []
        self.sub_cache = []

        self.r = praw.Reddit(user_agent=user_agent) #init praw

        if (DEVELOPER):
            print "DEVELOPER MODE ON (NO POSTING, NO LOGIN)"
        else:
            try:
                self.r.login(os.environ['UNCHART_REDDIT_USER'], os.environ['UNCHART_REDDIT_PASS'])
            except Exception, e:
                print "ERROR(@login): " + str(e)

    def build_post(self, urls):
        """
        Takes comment object and list of URLs of previously validated comment, iterates through URLs and matches item #s to CSV file values and builds a post
        that is ready to send to Reddit once it is returned from this method.
        RETURNS: Full post data
        """
        post_data = ""
        found_items = []
        for url in urls: #check for url pattern in comment body
            loadout_string = url.split('=',1)[1]
            loadout = loadout_string.split(',')
            for id in loadout:
                found_item = [s for s in loadout_data if id in s]
                found_items.append(found_item)
            if (len(found_items) > 1): #more than 1 items found in link
                post_data += "^(Loadout in) ^[link](%s) ^(as posted above)\r\n\r\n" % url
                for item in found_items:
                    post_data += "- **%s** - (%sLP)\r\n" % (item[0][1], item[0][2])
                del found_items[:]
                post_data += "\r\n\r\n---\r\n\r\n"
        if (DEVELOPER):
            print "[build_post]:\r\n %s" % post_data
            time.sleep(5)
        return post_data

    def valid_comment(self, comment): #returns list of urls if valid, false if invalid
        """
        check for a few things, post is after START_TIME, post is not by uncharted4loadout, and post has matched re pattern (for link)
        RETURNS: List of URLs matching our pattern
        """
        urls_to_return = []
        comment_utcunix = datetime.datetime.utcfromtimestamp(comment.created) - datetime.timedelta(hours=8) #offset from comment time as seen by the server to UTC
        start_utcunix = datetime.datetime.utcfromtimestamp(START_TIME)
        if (comment_utcunix > start_utcunix or DEVELOPER == True): #check comment time vs. bot start time with developer override
            if(not str(comment.author) == "uncharted4loadout" and comment.id not in self.cache):
                for url in re.findall(PATTERN, comment.body):
                    urls_to_return.append(url)
                if (DEVELOPER):
                    if (urls_to_return):
                        #print "[valid_comment (%s)]: %s" % (comment.id, urls_to_return)
                        pass
                return urls_to_return
            else:
                if (DEVELOPER):
                    #print "[valid_comment (%s)]: Returned False" % (comment.id)
                    pass
                return False

    def valid_submission(self, submission):
        """
        validates same as comment thread but for submissions specifically
        RETURNS: List of URLs matching our pattern
        """
        urls_to_return = []
        submission_utcunix = datetime.datetime.utcfromtimestamp(submission.created) - datetime.timedelta(hours=8)
        start_utcunix = datetime.datetime.utcfromtimestamp(START_TIME)
        if (submission_utcunix > start_utcunix or DEVELOPER == True):
            if (not str(submission.author) == 'uncharted4loadout' and submission.id not in self.sub_cache):
                for data in [submission.url, submission.selftext]:
                    for url in re.findall(PATTERN, data):
                        urls_to_return.append(url)
                    if (DEVELOPER):
                        if(urls_to_return):
                            print "[valid_submission (%s)]: %s" % (submission.id, urls_to_return)
                    return urls_to_return
            else:
                if (DEVELOPER):
                    print "[valid_submission (%s)]: Returned False" % (submission.id)
                return False

    def add_reply(self, comment, reply_text, reply_to):
        """
        Responsible for adding post to cache and attempting to send the post to Reddit.
        reply_to can be "comment" or "submission"
        RETRUNS: (none)
        """
        if reply_to == "comment":
            if (DEVELOPER):
                print "[add_reply(comment) %s]:" % str(comment.id)
                print reply_text + bot_signature
                self.cache.append(comment.id)
                time.sleep(5)
            else:
                self.cache.append(comment.id)
                try:
                    comment.reply(reply_text + bot_signature)
                except Exception, e:
                    print "ERROR(@add_reply(comment)): " + str(e)
                    self.cache.pop()
                    print self.cache
                    time.sleep(SLEEP_TIME)

        if reply_to == "submission":
            submission = comment
            if (DEVELOPER):
                print "[add_reply(submission) %s]:" % str(submission.id)
                print reply_text + bot_signature
                self.sub_cache.append(submission.id)
                time.sleep(5)
            else:
                self.sub_cache.append(submission.id)
                try:
                    submission.add_comment(reply_text + bot_signature)
                except Exception, e:
                    print "ERROR(@add_reply(submission)): " + str(e)
                    self.sub_cache.pop()
                    print self.sub_cache
                    time.sleep(SLEEP_TIME)



    def scan(self):
        """
        This is the workhorse for comments/submissions, will scan comments/submissions, pass comment/submission to validate method, if valid, it will
        return list of URLs found that we're looking for, pass those to the build_post method, and finally send the output to the add_reply method for posting.
        RETURNS: (none)
        """
        ################################COMMENTS
        try:
            sub_obj = self.r.get_subreddit(SUBREDDIT)
        except Exception, e:
            print "ERROR(@sublisting): " + str(e)

        try:
            for comment in sub_obj.get_comments(limit=20):
                if(self.valid_comment(comment)):
                    urls = self.valid_comment(comment)
                    print "SUCCESS(@scan_comments): Valid Comment Found (%s)" % comment.id
                    post_data = self.build_post(urls)
                    self.add_reply(comment, post_data,"comment")

        except Exception, e:
            print "ERROR(@commentPull): " + str(e)
            #print comment.body

        ################################SUBMISSIONS

        try:
            for submission in sub_obj.get_new(limit=20):
                if(self.valid_submission(submission)):
                    urls = self.valid_submission(submission)
                    print "SUCCESS(@scan_submissions): Valid Submission Found (%s)" % submission.id
                    post_data = self.build_post(urls)
                    self.add_reply(submission, post_data, "submission")

        except Exception, e:
            print "ERROR(@submissionPull): " + str(e)
            #print submission.selftext


    def return_cache(self):
        """
        Strictly for DEVELOPER mode to show posts being added to cache
        RETURNS: Current comment cache list
        """
        return self.cache


b = uncharted4_bot()
while True:
    if (DEVELOPER):
        print "--- Start"
    b.scan()
    if (DEVELOPER):
        print b.return_cache()
    time.sleep(SLEEP_TIME)
