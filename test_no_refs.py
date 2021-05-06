from unittest import TestCase
from unittest.mock import patch
from no_refs import Finder
from io import StringIO
import logging


class ProcessStreamTest(TestCase):
    def setUp(self):
        self.finder = Finder()


    @patch('no_refs.console_logger')
    def test_empty_input_produces_no_output(self, logger):
        stream = StringIO("")
        self.finder.process_stream(stream, "path")
        logger.assert_not_called()
        

    @patch('no_refs.console_logger')
    def test_no_page_node_produces_no_output(self, logger):
        stream = StringIO("""
        <mediawiki>
        </mediawiki>
        """)
        self.finder.process_stream(stream, "path")
        logger.assert_not_called()


    @patch('no_refs.console_logger')
    def test_no_revision_node_produces_no_output(self, logger):
        stream = StringIO("""
        <mediawiki>
          <page>
            <ns>0</ns>
          </page>
        </mediawiki>
        """)
        self.finder.process_stream(stream, "path")
        logger.assert_not_called()


    @patch('no_refs.console_logger')
    def test_empty_text_produces_no_output(self, logger):
        stream = StringIO("""
        <mediawiki>
          <page>
            <title>Title</title>
            <ns>0</ns>
            <id>1</id>
            <revision>
              <id>2</id>
              <text>
              </text>
            </revision>
          </page>
        </mediawiki>
        """)
        self.finder.process_stream(stream, "path")
        logger.info.assert_not_called()


    @patch('no_refs.console_logger')
    def test_one_revision_with_matching_text_finds_page(self, logger):
        stream = StringIO("""
        <mediawiki>
          <page>
            <title>Title 1</title>
            <ns>0</ns>
            <id>1</id>
            <revision>
              <id>2</id>
              <text>
                living people
              </text>
            </revision>
          </page>
        </mediawiki>
        """)
        self.finder.process_stream(stream, "path")
        logger.info.assert_called_once_with("Title 1")
