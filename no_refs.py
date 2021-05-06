from pathlib import Path
from argparse import ArgumentParser
import re
import bz2
from xml.dom.pulldom import parse, START_DOCUMENT, START_ELEMENT, END_ELEMENT, CHARACTERS
from datetime import datetime
import humanize
import logging
import logging.config
import sys
from dataclasses import dataclass

DUMP_ROOT = '/public/dumps/public/enwiki'

progress_logger = logging.getLogger('progress')
console_logger =  logging.getLogger('console')

class Page:
    def __init__(self):
        self.revisions = []


@dataclass
class Revision:
    id: int
    has_ref: bool


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
        self.doc = None
        self.page_data = None
        self.revision_data = None
        self.state = [self.start]


    def push(self, state):
        progress_logger.debug(f"push({state})")
        self.state.append(state)


    def pop(self):
        state = self.state.pop()
        progress_logger.debug(f"pop({state})")


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
        progress_logger.info(f"starting {path}")
        stream = bz2.open(path) if path.endswith('.bz2') else open(path)
        self.process_stream(stream, path)
        progress_logger.info(f"done with {path}")


    def process_stream(self, stream, path):
        """Stream is a file object, path is a string containing the
        human-readable name of the stream.  This is needed because the
        file object returned by bz2.open() doesn't support the name
        attribute.

        """
        self.path = path
        self.doc = parse(stream)
        self.cdata = []
        for event, node in self.doc:
            progress_logger.debug(f"{list(s.__name__ for s in self.state)}: {event}, {node}")
            if event == CHARACTERS:
                self.cdata.append(node.data)
                continue
            if event == START_ELEMENT:
                self.cdata = []
            self.state[-1](event, node)
        self.file_count += 1

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
            self.push(self.revision)


    def do_page(self):
        self.page_count += 1
        if self.page_count % 1000 == 0:
            self.log_progress()

        if self.page_data.ns != '0':
            return

        self.article_count += 1

        revisions = self.page_data.revisions
        progress_logger.debug(f"revisions={revisions}")
        if revisions == [] or any(rev.has_ref for rev in self.page_data.revisions):
            return

        self.found += 1
        title = self.page_data.title
        console_logger.info(title)
        progress_logger.info(f'Found "{title}" in {self.path}')


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
        if '#redirect' in self.content:
            return

        if 'living people' not in self.content:
            return

        self.blp_count += 1
        revision = Revision(self.revision_id, 'ref' in self.content)
        self.page_data.revisions.append(revision)


    def text(self, event, node):
        if event == END_ELEMENT and node.tagName == 'text':
            self.content = ''.join(self.cdata).lower()
            self.pop()


    def contributor(self, event, node):
        if event == END_ELEMENT and node.tagName == 'contributor':
            self.pop()


    def id(self, event, node):
        if event == END_ELEMENT and node.tagName == 'id':
            self.revision_id = int(''.join(self.cdata))
            self.pop()


    def get_text_from_singleton_node(self, node, tag):
        children = node.getElementsByTagName(tag)
        assert len(children) == 1
        cdata_nodes = children[0].childNodes
        return ''.join(n.nodeValue for n in cdata_nodes)


    def log_progress(self):
        dt = datetime.now() - self.t0
        progress_logger.info(f'Done with {self.file_count} files, '
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
    config = LOGGING_CONFIG.copy()
    config['handlers']['file']['filename'] = args.log or f'no-refs.log.{time_stamp}'
    logging.config.dictConfig(config)

    progress_logger.info(f'''command line: "{' '.join(sys.argv)}"''')
    progress_logger.info(f'started at {time_stamp}')

    finder = Finder()
    if args.file:
        finder.process_file(args.file)
    else:
        finder.process_directory(args.dump_name)

    progress_logger.info('all done')
    finder.log_progress()



LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'file_formatter': {
            'format': '%(asctime)s %(levelname)s: %(message)s',
        },
        'console_formatter': {
            'format': '%(message)s',
        }
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': None,
            'mode': 'w',  # https://bugs.python.org/issue27805
            'formatter': 'file_formatter',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        'progress': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'console': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


if __name__ == '__main__':
    main()
