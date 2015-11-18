from BeautifulSoup import BeautifulSoup
from PIL import Image
import urllib2 as urllib
from multiprocessing import Pool
import io


def get_and_convert_image(args):
    image_counter, img_src = args
    try:
        print 'Downloading image', img_src
        fd = urllib.urlopen(img_src)
        u = fd.read()
        if len(u) is 0:
            return None, None
        image_file = io.BytesIO(u)
        im = Image.open(image_file)
        w, h = im.size
        if w is 0 or h is 0:
            return None, None
        img_path = 'images/image-%d.jpg' % (image_counter)
        im.convert('RGB').save(img_path, 'JPEG')
        data_fp = open(img_path, 'rb')
        data_uri = data_fp.read().encode('base64').replace('\n', '')
        img_data = 'data:image/{0};base64,{1}'.format('jpeg', data_uri)
        print '[*] Returning %s %d' % (img_src, len(img_data))
        return (img_src, img_data)
    except Exception, e:
        print 'Invalid Image'
        print str(e)
        return None, None


def download_html(data):
    image_counter = 1
    soup = BeautifulSoup(data.replace('\n', ''))
    z1 = soup.find('h1').text if soup.find('h1') else ''
    z2 = soup.find('title').text if soup.find('title') else ''
    title = z1 if len(z2) < len(z1) else z2
    """
    title = z.translate(
        {ord(c): "-" for c in "!@#$%^&*()[]{};:,./<>?\|`~-=_+"}
    )
    """
    title = title.replace(':', ' -')
    print title
    image_replacement = {}
    images = []
    pool = Pool(5)
    for img in soup.findAll('img'):
        img_src = img['src'] if img and img.get('src') else None
        if img_src:
           img_src = str(img_src).strip()
        if not img_src or len(img_src) is 0:
            continue
        images.append((image_counter, img_src))
        image_counter += 1

    results = pool.map(get_and_convert_image, images)
    op = '%s.html' % title
    sp = '<html><body>' + str(soup.find('div', {'class': 'reader_content'})) + '<body></html>'
    for k, v in results:
        if not (k and v):
            continue
        sp = sp.replace(k, v)
    with open(op, 'w') as _f:
        _f.write(sp)
    return op


def get_title_link_by_element(element):
    try:
        a = element.find('a', {'class': 'title'})
        link = dict(a.attrs)['href']
        title = a.text
        return dict(id=link, title=title, link='https://getpocket.com%s' % link)
    except Exception, e:
        print str(e)
        return {}


def get_list(data):
    soup = BeautifulSoup(data.replace('\n', ''))
    pool = Pool(5)
    divs = soup.findAll('div', {'class': 'item_content'})
    articles = {}
    results = map(get_title_link_by_element, divs)
    articles = {}
    for result in results:
        print result
        if len(result) < 3:
            continue
        articles[result['id']] = result
    return articles


if __name__ == '__main__':
    data = open('Pocket - How (and Why) SpaceX Will Colonize Mars.html').read()
    print download_html(data)
