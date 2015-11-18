import os.path
import zipfile
from BeautifulSoup import BeautifulSoup
from PIL import Image
import urllib2 as urllib
import io

images = []

epub = zipfile.ZipFile('my_book.epub', 'w')
epub.writestr("mimetype", "application/epub+zip\n")
html_files = ['test.html']
epub.writestr("META-INF/container.xml", '''<container version="1.0"
              xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
              <rootfile full-path="OEBPS/Content.opf" media-type="application/oebps-package+xml"/
              </rootfiles>
              /container>\n''');

index_tpl = '''<package version="2.0"
  xmlns="http://www.idpf.org/2007/opf">
  <metadata/>
  <manifest>
    %(manifest)s
  </manifest>
  <spine toc="ncx">
    %(spine)s
  </spine>
</package>\n'''

manifest = ""
spine = ""

image_counter = 1

# Write each HTML file to the ebook, collect information for the index
for i, html in enumerate(html_files):
    basename = os.path.basename(html)
    soup = BeautifulSoup(open(html).read().replace('\n', ''))
    for img in soup.findAll('img'):
        try:
            print 'Downloading image', img['src']
            fd = urllib.urlopen(img['src'])
            image_file = io.BytesIO(fd.read())
            im = Image.open(image_file)
            img_path = 'images/image-%d.%s' % (image_counter, im.format.lower())
            im.save(img_path)
            image_counter += 1
            images.append((img_path, os.path.basename(img_path)))
            img['src'] = os.path.basename(img_path)
        except Exception, e:
            print 'Invalid Image', img['src']
            print str(e)
            img['src'] = ''
    manifest += '<item id="file_%s" href="%s" media-type="application/xhtml+xml"/>' % (i+1, basename)
    spine += '<itemref idref="file_%s" />' % (i+1)
    str(soup)
    epub.writestr('OEBPS/'+basename, str(soup) + '\n')

for img, bp_img in images:
    print 'Adding this one here', img
    epub.write(img, 'OEBPS/'+bp_img)

# Finally, write the index
print manifest
print spine
epub.writestr('OEBPS/Content.opf', index_tpl % {
  'manifest': manifest,
  'spine': spine,
})
