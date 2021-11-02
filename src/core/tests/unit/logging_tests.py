import logging
from django.test import SimpleTestCase

class TestLogging(SimpleTestCase):
    def test_logging(self):
        with self.assertLogs('bar', level='DEBUG') as cm:
            logging.getLogger('bar').debug('first message')
            logging.getLogger('bar.foo').info('second message')
        self.assertEqual(cm.output, ['DEBUG:bar:first message',
                                        'INFO:bar.foo:second message'])

        with self.assertLogs('foo', level='INFO') as cm:
            logging.getLogger('foo').info('first message')
            logging.getLogger('foo.bar').error('second message')
        self.assertEqual(cm.output, ['INFO:foo:first message',
                                        'ERROR:foo.bar:second message'])

        with self.assertLogs('foo', level='ERROR') as cm:
            logging.getLogger('foo').error('first message')
            logging.getLogger('foo.bar').error('second message')
        self.assertEqual(cm.output, ['ERROR:foo:first message',
                                        'ERROR:foo.bar:second message'])
