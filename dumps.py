from pathlib import Path
import re
import bz2
import xml.sax

DUMP_DIR = Path('/public/dumps/public/enwiki/latest')

class Handler(xml.sax.handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_text = False
        self.title = None

        
    def startElement(self, name, attrs):
        if name == 'title':
            self.in_title = True
        elif name == 'text':
            self.in_text = True

    def endElement(self, name):
        if name == 'title':
            self.in_title = False
        elif name == 'text':
            self.in_text = False

    def characters(self, content):
        if self.in_title:
            self.title = content
            print()
            print('------------------------------------')
            print(self.title)
        if self.in_text:
            print(content, end='')
            



def main():
    paths = []
    for path in DUMP_DIR.glob('enwiki-latest-pages-articles[123456789]*.xml-p*bz2'):
        m = re.match(r'.*xml-p([0-9]*)p([0-9]*)', path.name)
        key = int(m.group(1))
        paths.append((key, path))
    paths.sort()
    key, path = paths[0]
    handler = Handler()
    xml.sax.parse(bz2.open(path), handler)



if __name__ == '__main__':
    main()
