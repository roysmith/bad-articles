from pathlib import Path
from argparse import ArgumentParser
import re
import bz2
from xml.dom import pulldom
from datetime import datetime
import humanize
import logging
import sys

DUMP_ROOT = '/public/dumps/public/enwiki'

PAGE = object()

class Finder:
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

    def process_directory(self, dump_name):
        dump_dir = Path(DUMP_ROOT) / dump_name
        paths = []
        for path in dump_dir.glob(f'enwiki-{dump_name}-pages-articles[123456789]*.xml-p*bz2'):
            m = re.match(r'.*xml-p([0-9]*)p([0-9]*)', path.name)
            key = int(m.group(1))
            paths.append((key, path))
        paths.sort()

        for key, path in paths:
            self.file_count += 1
            self.process_file(str(path))


    def process_file(self, path):
        self.path = path
        stream = bz2.open(path) if path.endswith('.bz2') else open(path)
        self.doc = pulldom.parse(stream)
        title = None
        for event, node in self.doc:
            if event == pulldom.START_ELEMENT and node.tagName == 'page':
                self.do_page(node)


    def do_page(self, node):
        self.progress()
        self.doc.expandNode(node)
        if self.get_text_from_singleton_node(node, 'ns') != '0':
            return

        title_nodes = node.getElementsByTagName('title')
        assert len(title_nodes) == 1
        cdata_nodes = title_nodes[0].childNodes
        title = self.get_text_from_singleton_node(node, 'title')

        self.article_count += 1
        content = self.get_text_from_singleton_node(node, 'text').lower()
        if '#redirect' in content:
            return

        if 'living people' in content:
            self.blp_count += 1
            if not 'ref' in content:
                self.found += 1
                print(title)
                logging.info(f'Found "{title}" in {self.path}')


    def get_text_from_singleton_node(self, node, tag):
        children = node.getElementsByTagName(tag)
        assert len(children) == 1
        cdata_nodes = children[0].childNodes
        return ''.join(n.nodeValue for n in cdata_nodes)


    def progress(self):
        self.page_count += 1
        if self.page_count % 1000 == 0:
            self.log_progress()

    def log_progress(self):
        dt = datetime.now() - self.t0
        logging.info(f'Done with {self.file_count} files, '
                     f'{humanize.intcomma(self.page_count)} pages, '
                     f'{humanize.intcomma(self.article_count)} articles '
                     f'{humanize.intcomma(self.blp_count)} blps, '
                     f'found {self.found} in {dt}')


def main():
    parser = ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file')
    input_group.add_argument('--dump_name')

    args = parser.parse_args()

    time_stamp = datetime.utcnow().replace(microsecond=0).isoformat()
    logging.basicConfig(filename=f'no-refs.log.{time_stamp}',
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
