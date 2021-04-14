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
        print(path)

if __name__ == '__main__':
    main()
