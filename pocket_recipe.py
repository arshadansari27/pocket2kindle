"""
Pocket Calibre Recipe v1.4
"""
from string import Template
import json
import operator
import re
import tempfile
import urllib
import urllib2


__license__ = 'GPL v3'
__copyright__ = '''
2010, Darko Miletic <darko.miletic at gmail.com>
2011, Przemyslaw Kryger <pkryger at gmail.com>
2012-2013, tBunnyMan <Wag That Tail At Me dot com>
'''


class Pocket(object):
    title = 'Pocket'
    __author__ = 'Darko Miletic, Przemyslaw Kryger, Keith Callenberg, tBunnyMan'
    description = '''Personalized news feeds. Go to getpocket.com to setup up
                  your news. This version displays pages of articles from
                  oldest to newest, with max & minimum counts, and marks
                  articles read after downloading.'''
    publisher = 'getpocket.com'
    category = 'news, custom'

    oldest_article        = 7.0
    max_articles_per_feed = 50
    minimum_articles      = 10
    mark_as_read_after_dl = True  # Set this to False for testing
    sort_method           = 'oldest'  # MUST be either 'oldest' or 'newest'
    # To filter by tag this needs to be a single tag in quotes; IE 'calibre'
    only_pull_tag         = None

    #You don't want to change anything under
    no_stylesheets = True
    use_embedded_content = False
    needs_subscription = True
    articles_are_obfuscated = True
    apikey = '19eg0e47pbT32z4793Tf021k99Afl889'
    index_url = u'https://getpocket.com'
    read_api_url = index_url + u'/v3/get'
    modify_api_url = index_url + u'/v3/send'
    legacy_login_url = index_url + u'/l'  # We use this to cheat oAuth
    articles = []

    def get_browser(self, *args, **kwargs):
        """
        We need to pretend to be a recent version of safari for the mac to
        prevent User-Agent checks Pocket api requires username and password so
        fail loudly if it's missing from the config.
        """
        br = BasicNewsRecipe.get_browser(self,
                user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; \
                        en-us) AppleWebKit/533.19.4 (KHTML, like Gecko) \
                        Version/5.0.3 Safari/533.19.4')
        if self.username is not None and self.password is not None:
            br.open(self.legacy_login_url)
            br.select_form(nr=0)
            br['feed_id'] = self.username
            br['password'] = self.password
            br.submit()
        else:
            self.user_error("This Recipe requires authentication")
        return br

    def get_auth_uri(self):
        """Quick function to return the authentication part of the url"""
        uri = ""
        uri = u'{0}&apikey={1!s}'.format(uri, self.apikey)
        if self.username is None or self.password is None:
            self.user_error("Username or password is blank.")
        else:
            uri = u'{0}&username={1!s}'.format(uri, self.username)
            uri = u'{0}&password={1!s}'.format(uri, self.password)
        return uri

    def get_pull_articles_uri(self):
        uri = ""
        uri = u'{0}&state={1}'.format(uri, u'unread')
        uri = u'{0}&contentType={1}'.format(uri, u'article')
        uri = u'{0}&sort={1}'.format(uri, self.sort_method)
        uri = u'{0}&count={1!s}'.format(uri, self.max_articles_per_feed)
        if self.only_pull_tag is not None:
            uri = u'{0}&tag={1}'.format(uri, self.only_pull_tag)
        return uri

    def parse_index(self):
        pocket_feed = []
        fetch_url = u"{0}?{1}{2}".format(
            self.read_api_url,
            self.get_auth_uri(),
            self.get_pull_articles_uri()
        )
        try:
            request = urllib2.Request(fetch_url)
            response = urllib2.urlopen(request)
            pocket_feed = json.load(response)['list']
        except urllib2.HTTPError as e:
            self.log.exception("Pocket returned an error: {0}".format(e.info()))
            return []
        except urllib2.URLError as e:
            self.log.exception("Unable to connect to getpocket.com's api: {0}\nurl: {1}".format(e, fetch_url))
            return []

        if len(pocket_feed) < self.minimum_articles:
            self.mark_as_read_after_dl = False
            self.user_error("Only {0} articles retrieved, minimum_articles not reached".format(len(pocket_feed)))

        for pocket_article in pocket_feed.iteritems():
            self.articles.append({
                'item_id':      pocket_article[0],
                'title':        pocket_article[1]['resolved_title'],
                'date':         pocket_article[1]['time_updated'],
                'url':          u'{0}/a/read/{1}'.format(self.index_url, pocket_article[0]),
                'real_url':     pocket_article[1]['resolved_url'],
                'description':  pocket_article[1]['excerpt'],
                'sort':         pocket_article[1]['sort_id']
            })
        self.articles = sorted(self.articles, key=operator.itemgetter('sort'))
        return [("My Pocket Articles for {0}".format(strftime('[%I:%M %p]')), self.articles)]

    def get_textview(self, url):
        """
        Since Pocket's v3 API they removed access to textview. They also
         redesigned their page to make it much harder to scrape their textview.
         We need to pull the article, retrieve the formcheck id, then use it
         to querty for the json version
        This function will break when pocket hates us
        """
        ajax_url = self.index_url + u'/a/x/getArticle.php'
        soup = self.index_to_soup(url)
        fc_tag = soup.find('script', text=re.compile("formCheck"))
        fc_id = re.search(r"formCheck = \'([\d\w]+)\';", fc_tag).group(1)
        article_id = url.split("/")[-1]
        data = urllib.urlencode({'itemId': article_id, 'formCheck': fc_id})
        try:
            response = self.browser.open(ajax_url, data)
        except urllib2.HTTPError as e:
            self.log.exception("unable to get textview {0}".format(e.info()))
            raise e
        return json.load(response)['article']

    def get_obfuscated_article(self, url):
        """
        Our get_textview returns parsed json so prettify it to something well
        parsed by calibre.
        """
        article = self.get_textview(url)
        template = Template('<h1>$title</h1><div class="body">$body</div>')
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tmpbody = article['article']
            for img in article['images']:
                imgdiv = '<div id="RIL_IMG_{0}" class="RIL_IMG"></div>'.format(article['images'][img]['image_id'])
                imgtag = '<img src="{0}" \>'.format(article['images'][img]['src'])
                tmpbody = tmpbody.replace(imgdiv, imgtag)

            tf.write(template.safe_substitute(
                title=article['title'],
                body=tmpbody
                ))
        return tf.name

    def mark_as_read(self, mark_list):
        actions_list = []
        for article_id in mark_list:
            actions_list.append({
                'action': 'archive',
                'item_id': article_id
            })
        mark_read_url = u'{0}?actions={1}{2}'.format(
            self.modify_api_url,
            json.dumps(actions_list, separators=(',', ':')),
            self.get_auth_uri()
        )
        try:
            request = urllib2.Request(mark_read_url)
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            self.log.exception('Pocket returned an error while archiving articles: {0}'.format(e))
            return []
        except urllib2.URLError as e:
            self.log.exception("Unable to connect to getpocket.com's modify api: {0}".format(e))
            return []

    def cleanup(self):
        if self.mark_as_read_after_dl:
            self.mark_as_read([x['item_id'] for x in self.articles])
        else:
            pass

    def default_cover(self, cover_file):
        """
        Create a generic cover for recipes that don't have a cover
        This override adds time to the cover
        """
        try:
            from calibre.ebooks import calibre_cover
            title = self.title if isinstance(self.title, unicode) else \
                self.title.decode('utf-8', 'replace')
            date = strftime(self.timefmt)
            time = strftime('[%I:%M %p]')
            img_data = calibre_cover(title, date, time)
            cover_file.write(img_data)
            cover_file.flush()
        except:
            self.log.exception('Failed to generate default cover')
            return False
        return True

    def user_error(self, error_message):
        if hasattr(self, 'abort_recipe_processing'):
            self.abort_recipe_processing(error_message)
        else:
            self.log.exception(error_message)
            raise RuntimeError(error_message)

# vim:ft=python tabstop=8 expandtab shiftwidth=4 softtabstop=4
