from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
import time
import simplejson as json
from html_generation import download_html, get_list
from mailer import mail
import os
from settings import KINDLE_MAIL, KINDLE_FOLDER, USER_EMAIL, USER_PASSWD


id_stuff = {}
driver = None


def readystate_complete(d):
    return d.execute_script("return document.readyState") == "complete"


def load_articles():
    try:
        data = open('list.json', 'r').read()
        if not data and len(data) is 0:
            return {}
        return json.loads(data)
    except:
        return {}


def save_articles(articles):
    with open('list.json', 'w') as _f:
        _f.write(json.dumps(articles))


def login():
    global driver
    driver = webdriver.Firefox()
    # driver = webdriver.PhantomJS('phantomjs')
    # driver.set_window_size(1120, 550)
    driver.get("https://getpocket.com/a")
    print driver.page_source
    first = True
    while driver and 'Log In' in driver.title:
        print '[*]', driver.title, first
        if not first:
            time.sleep(4)
        first = False
        try:
            username_elem = driver.find_element_by_id('feed_id')
            username_elem.send_keys(USER_EMAIL)
            password_elem = driver.find_element_by_id('login_password')
            password_elem.send_keys(USER_PASSWD)
            password_elem.send_keys(Keys.RETURN)
            print 'loggnig in'
            WebDriverWait(driver, 60).until(readystate_complete)
            print 'Successfully logged in'
        except:
            print 'Something went wrong, retrying...'
            raise


def reload_articles(force=False):
    global driver
    articles = load_articles()
    try:
        prev_length = 0
        try:
            page_source = open('page_source.html', 'r').read()
        except:
            page_source = None
        if not page_source or force:
            if not driver:
                login()
            while True:
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                curr_length = len(driver.page_source)
                if prev_length == curr_length:
                    break
                prev_length = curr_length
            page_source = driver.page_source

        with open('page_source.html', 'w') as _f:
            _f.write(page_source.encode('utf-7'))
        time.sleep(1)
        articles = get_list(page_source)
        save_articles(articles)
    except Exception:
        raise
    return articles


def load_article(link):
    print 'Loading...', link
    if 'getpocket' not in link:
        print 'External Link cannot be downloaded'
        return
    try:
        if not driver:
            login()
        driver.get(link)
        WebDriverWait(driver, 60).until(readystate_complete)
        prev_length = 0
        while True:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            curr_length = len(driver.page_source)
            if prev_length == curr_length:
                break
            prev_length = curr_length
            print 'loading...'
        time.sleep(2)

        article = download_html(driver.page_source)
        print 'Downloaded at', article
        np = '%s%s' % (KINDLE_FOLDER, article)
        if os.path.exists(np):
            os.remove(np)
        os.rename(article, np)
        choice = raw_input('Would you like to send to kindle (y/N)').strip()
        if choice in ['y', 'Y']:
            mail(KINDLE_MAIL, '', article, np)
    except Exception, e:
        print '[*] Error: Something went wrong'
        print str(e)


def logout():
    global driver
    driver.close()


# reload_articles()
def list_articles(articles):
    print 'Article List'
    i = 1
    for k, v in articles.iteritems():
        id_stuff[i] = k
        lines = v['title'].split('\n')
        if len(lines) > 1:
            line, source = lines[0], lines[1]
        else:
            line, source = lines[0], ''
        print '[%d] %s %s' % (i, line, source)
        i += 1


def menu():
    articles = load_articles()
    print 'Select what you wanna do'
    print '1. Reload Articles'
    print '1f. Force Reload Articles'
    print '2. List Articles'
    print '3. Download Article'
    print '4. Send Article To Kindle'
    print '5. Exit'
    choice = raw_input().strip()
    if choice is '1':
        articles = reload_articles()
        list_articles(articles)
    elif choice is '1f':
        articles = reload_articles(force=True)
        list_articles(articles)
    elif choice is '2':
        list_articles(articles)
    elif choice is '3':
        art = raw_input('Select article number to download:').strip()
        try:
            art = int(art)
            if art not in id_stuff:
                print 'Invalid Article Selected'
                return
            article_id = id_stuff[art]
            print '[*] Downloading'
            print articles[article_id]['title']
            load_article(articles[article_id]['link'])
        except:
            print 'Invalid article choice'
    elif choice is '4':
        files = os.listdir(KINDLE_FOLDER)
        file_dict = {}
        for i, f in enumerate(files):
            file_dict[str(i)] = f
            print '[%d] %s' % (i, f)
        ch = raw_input('select the file to send:')
        ch = str(ch.strip())
        if ch not in file_dict:
            print 'Invalid choice'
            return
        file_to_send = file_dict[ch]
        mail(KINDLE_MAIL, '', file_to_send, '%s%s' % (KINDLE_FOLDER,
                                                      file_to_send))
    elif choice is '5':
        print 'Exiting'
        if driver:
            try:
                driver.close()
            except:
                pass
        exit()
    else:
        print 'Invalid choice'

if __name__ == '__main__':
    while True:
        menu()
