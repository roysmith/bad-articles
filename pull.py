from pathlib import Path
import re
import bz2
from xml.dom import pulldom
from datetime import datetime
import humanize

DUMP_DIR = Path('/public/dumps/public/enwiki/latest')

file_count = 0
page_count = 0
blp_count = 0
found = 0
t0 = datetime.now()

def main():
    global file_count
    paths = []
    for path in DUMP_DIR.glob('enwiki-latest-pages-articles[123456789]*.xml-p*bz2'):
        m = re.match(r'.*xml-p([0-9]*)p([0-9]*)', path.name)
        key = int(m.group(1))
        paths.append((key, path))
    paths.sort()

    for key, path in paths:
        file_count += 1
        process_file(path)


def process_file(path):
    global file_count, page_count, blp_count, found
    doc = pulldom.parse(bz2.open(path))
    for event, node in doc:
        if event == pulldom.START_ELEMENT and node.tagName == 'page':
            page_count += 1
            if page_count % 1000 == 0:
                dt = datetime.now() - t0
                print(f'Done with {file_count} files, {humanize.intcomma(page_count)} pages, {humanize.intcomma(blp_count)} blps, found {found} in {dt}')
            doc.expandNode(node)
            title = node.getElementsByTagName('title')[0].childNodes[0].nodeValue
            cdataNodes = node.getElementsByTagName('text')[0].childNodes
            content = ' '.join(node.nodeValue for node in cdataNodes).lower()
            if 'living people' in content:
                blp_count += 1
                if not 'ref' in content:
                    found += 1
                    print('==>', title)


if __name__ == '__main__':
    main()
