from pathlib import Path
import re
import bz2
from xml.dom import pulldom
from datetime import datetime
import humanize

DUMP_DIR = Path('/public/dumps/public/enwiki/latest')

page_count = 0
blp_count = 0
found = 0
t0 = datetime.now()


def main():
    process_file('/public/dumps/public/enwiki/20210320/enwiki-20210320-pages-articles.xml.bz2')


def process_file(path):
    global page_count, blp_count, found
    doc = pulldom.parse(bz2.open(path))
    for event, node in doc:
        if event == pulldom.START_ELEMENT and node.tagName == 'page':
            page_count += 1
            if page_count % 1000 == 0:
                dt = datetime.now() - t0
                print(f'Done with {humanize.intcomma(page_count)} pages, {humanize.intcomma(blp_count)} blps, found {found} in {dt}')
            doc.expandNode(node)
            ns = node.getElementsByTagName('ns')[0].childNodes[0].nodeValue
            title = node.getElementsByTagName('title')[0].childNodes[0].nodeValue
            if not ns == '0':
                continue

            cdataNodes = node.getElementsByTagName('text')[0].childNodes
            content = ' '.join(node.nodeValue for node in cdataNodes).lower()
            if '#redirect' in content:
                continue

            if 'living people' in content:
                blp_count += 1
                if not 'ref' in content:
                    found += 1
                    print('Found:', title)


if __name__ == '__main__':
    main()
