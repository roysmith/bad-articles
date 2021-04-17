from pathlib import Path
from argparse import ArgumentParser
import re
import bz2
from xml.dom import pulldom
from datetime import datetime
import humanize

DUMP_ROOT = '/public/dumps/public/enwiki'
DUMP_NAME = 'latest'

class Finder:
    def __init__(self, dump_name):
        self.dump_name = dump_name
        self.file_count = 0
        self.page_count = 0
        self.article_count = 0
        self.blp_count = 0
        self.found = 0
        self.t0 = datetime.now()

    def process_directory(self):
        dump_dir = Path(DUMP_ROOT) / self.dump_name
        paths = []
        for path in dump_dir.glob(f'enwiki-{self.dump_name}-pages-articles[123456789]*.xml-p*bz2'):
            m = re.match(r'.*xml-p([0-9]*)p([0-9]*)', path.name)
            key = int(m.group(1))
            paths.append((key, path))
        paths.sort()

        for key, path in paths:
            self.file_count += 1
            self.process_file(path)


    def process_file(self, path):
        stream = bz2.open(path) if path.endswith('.bz2') else open(path)
        doc = pulldom.parse(stream)
        title = None
        previous_title = None
        for event, node in doc:
            if event == pulldom.START_ELEMENT and node.tagName == 'page':
                self.report_progress()
                doc.expandNode(node)
                ns = self.get_text_from_singleton_node(node, 'ns')
                previous_title = title
                title_nodes = node.getElementsByTagName('title')
                assert len(title_nodes) == 1
                cdata_nodes = title_nodes[0].childNodes
                title = self.get_text_from_singleton_node(node, 'title')
                if not ns == '0':
                    continue

                self.article_count += 1
                content = self.get_text_from_singleton_node(node, 'text').lower()
                if '#redirect' in content:
                    continue

                if 'living people' in content:
                    self.blp_count += 1
                    if not 'ref' in content:
                        self.found += 1
                        print(f'Found "{title}" ({repr(title)}, previous="{previous_title}") in {path}')


    def get_text_from_singleton_node(self, node, tag):
        children = node.getElementsByTagName(tag)
        assert len(children) == 1
        cdata_nodes = children[0].childNodes
        return ''.join(n.nodeValue for n in cdata_nodes)


    def report_progress(self):
        self.page_count += 1
        if self.page_count % 1000 == 0:
            dt = datetime.now() - self.t0
            print((f'Done with {self.file_count} files, '
                   f'{humanize.intcomma(self.page_count)} pages, '
                   f'{humanize.intcomma(self.article_count)} articles '
                   f'{humanize.intcomma(self.blp_count)} blps, '
                   f'found {self.found} in {dt}'))

def main():
    parser = ArgumentParser()
    parser.add_argument('--file')
    parser.add_argument('--xml')
    args = parser.parse_args()
    
    finder = Finder(DUMP_NAME)
    file = args.file
    if file:
        finder.process_file(file)
    else:
        finder.process_directory()


if __name__ == '__main__':
    main()
