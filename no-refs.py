from pathlib import Path
from argparse import ArgumentParser
import re
import bz2
from xml.dom.pulldom import parse, START_DOCUMENT, START_ELEMENT, END_ELEMENT, CHARACTERS
from datetime import datetime
import humanize
import logging
import sys

DUMP_ROOT = '/public/dumps/public/enwiki'

PAGE = object()

class Page:
    def __init__(self):
        self.revisions = []


class Revision:
    pass


class Finder:
    """docstring"""


    def __init__(self):
        self.path = None
        self.file_count = 0
        self.page_count = 0
        self.article_count = 0
        self.blp_count = 0
        self.found = 0
        self.t0 = datetime.now()
        self.path = None
        self.doc = None
        self.page_data = None
        self.revision_data = None
        self.state = [self.start]


    def push(self, state):
        logging.debug(f"push({state})")
        self.state.append(state)


    def pop(self):
        state = self.state.pop()
        logging.debug(f"pop({state})")


    def process_directory(self, dump_name):
        dump_dir = Path(DUMP_ROOT) / dump_name
        paths = []
        for path in dump_dir.glob(f'enwiki-{dump_name}-pages-articles[123456789]*.xml-p*bz2'):
            m = re.match(r'.*xml-p([0-9]*)p([0-9]*)', path.name)
            key = int(m.group(1))
            paths.append((key, path))
        paths.sort()

        for key, path in paths:
            self.process_file(str(path))


    def process_file(self, path):
        self.path = path
        logging.info(f"starting {path}")
        stream = bz2.open(path) if path.endswith('.bz2') else open(path)
        self.doc = parse(stream)
        self.cdata = []
        for event, node in self.doc:
            logging.debug(f"{list(s.__name__ for s in self.state)}: {event}, {node}")
            if event == CHARACTERS:
                self.cdata.append(node.data)
                continue
            if event == START_ELEMENT:
                self.cdata = []
            self.state[-1](event, node)
        self.file_count += 1
        logging.info(f"done with {path}")

    def start(self, event, node):
        if event == START_DOCUMENT:
            self.push(self.document)


    def document(self, event, node):
        if event == START_ELEMENT and node.tagName == 'mediawiki':
            self.push(self.mediawiki)


    def mediawiki(self, event, node):
        if event == END_ELEMENT and node.tagName == 'mediawiki':
            self.pop()
        if event == START_ELEMENT and node.tagName == 'page':
            self.page_data = Page()
            self.push(self.page)


    def page(self, event, node):
        if event == END_ELEMENT and node.tagName == 'page':
            self.do_page()
            self.page_data = None
            self.pop()
        if event == START_ELEMENT and node.tagName == 'title':
            self.push(self.title)
        if event == START_ELEMENT and node.tagName == 'ns':
            self.push(self.ns)
        if event == START_ELEMENT and node.tagName == 'revision':
            self.revision_data = Revision()
            self.push(self.revision)


    def do_page(self):
        self.page_count += 1
        if self.page_count % 1000 == 0:
            self.log_progress()

        self.article_count += 1


    def title(self, event, node):
        if event == END_ELEMENT and node.tagName == 'title':
            self.page_data.title = ''.join(self.cdata)
            self.pop()


    def ns(self, event, node):
        if event == END_ELEMENT and node.tagName == 'ns':
            self.page_data.ns = ''.join(self.cdata)
            self.pop()


    def revision(self, event, node):
        if event == END_ELEMENT and node.tagName == 'revision':
            self.do_revision()
            self.revision_data = None
            self.pop()
        if event == START_ELEMENT and node.tagName == 'id':
            self.push(self.id)
        if event == START_ELEMENT and node.tagName == 'contributor':
            self.push(self.contributor)
        if event == START_ELEMENT and node.tagName == 'text':
            self.push(self.text)


    def do_revision(self):
        if self.page_data.ns != '0':
            return

        content = self.revision_data.text.lower()
        if '#redirect' in content:
            return

        if 'living people' not in content:
            return

        self.blp_count += 1
        if 'ref' in content:
            return

        self.found += 1
        title = self.page_data.title
        print(title)
        logging.info(f'Found "{title}" in {self.path}')


    def text(self, event, node):
        if event == END_ELEMENT and node.tagName == 'text':
            self.revision_data.text = ''.join(self.cdata)
            self.pop()


    def contributor(self, event, node):
        if event == END_ELEMENT and node.tagName == 'contributor':
            self.pop()


    def id(self, event, node):
        if event == END_ELEMENT and node.tagName == 'id':
            self.revision_data.id = ''.join(self.cdata)
            self.pop()


    def get_text_from_singleton_node(self, node, tag):
        children = node.getElementsByTagName(tag)
        assert len(children) == 1
        cdata_nodes = children[0].childNodes
        return ''.join(n.nodeValue for n in cdata_nodes)


    def log_progress(self):
        dt = datetime.now() - self.t0
        logging.info(f'Done with {self.file_count} files, '
                     f'{humanize.intcomma(self.page_count)} pages, '
                     f'{humanize.intcomma(self.article_count)} articles '
                     f'{humanize.intcomma(self.blp_count)} blps, '
                     f'found {self.found} in {dt}')


def main():
    parser = ArgumentParser()
    parser.add_argument('--log')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file')
    input_group.add_argument('--dump_name')

    args = parser.parse_args()

    time_stamp = datetime.utcnow().replace(microsecond=0).isoformat()
    logging.basicConfig(filename=args.log or f'no-refs.log.{time_stamp}',
                        filemode='w',  # https://bugs.python.org/issue27805
                        format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)
    logging.info(f'''command line: "{' '.join(sys.argv)}"''')
    logging.info(f'started at {time_stamp}')

    finder = Finder()
    if args.file:
        finder.process_file(args.file)
    else:
        finder.process_directory(args.dump_name)

    logging.info('all done')
    finder.log_progress()


if __name__ == '__main__':
    main()
