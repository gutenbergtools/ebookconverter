from csv import DictReader, DictWriter, excel
from urllib.parse import urljoin
import re
from io import BytesIO
from PIL import Image, ImageFile
import hashlib

ImageFile.LOAD_TRUNCATED_IMAGES = True
DESTDIR = '/export/sunsite/users/gutenbackend/cache/epub/{item}/'

ITEMMATCH = re.compile(r'files/(\d+)/')
PATHMATCH = re.compile(r'/export/sunsite/users/gutenbackend/cache/epub/\d+/')
infilename = 'sample_alt_log.log'
outfilename = 'img_data.csv'
lineno = 0
innames = ['datetime', 'src', 'img_id', 'alt_txt', 'rel_url', 'in_a_figure']
outnames = ['item', 'img_id', 'alt_txt', 'img_url', 'in_a_figure', 'x', 'y', 'len', 'hash']
with open(infilename,'r') as infile:
    sheetreader = DictReader(infile, dialect=excel, fieldnames=innames)
    with open(outfilename, 'w') as outfile:
        sheetwriter = DictWriter(outfile, dialect=excel, fieldnames=outnames, extrasaction='ignore')
        for altdata in sheetreader:
            lineno += 1
            itemmatch = ITEMMATCH.search(altdata['src'])
            if itemmatch:
                altdata['item'] = itemmatch.group(1)
            else:
                continue
            destdir = DESTDIR.format(**altdata)
            path = urljoin(destdir, altdata['rel_url'])
            altdata['img_url'] = PATHMATCH.sub('', path)
            try:
                with open(path, 'rb') as fp:
                    image_data = fp.read()
                    altdata['hash'] = hashlib.sha256(image_data).hexdigest()
                    altdata['len'] = len(image_data)
                    bio = BytesIO(image_data)
                    unsized_image = Image.open(bio)
                    altdata['x'], altdata['y'] = unsized_image.size
            except IOError as e:
                print(e)
            altdata["alt_txt"] = altdata["alt_txt"][:2000] if altdata["alt_txt"] else ''
            sheetwriter.writerow(altdata)
print(f"finished loading {lineno} imgs")
