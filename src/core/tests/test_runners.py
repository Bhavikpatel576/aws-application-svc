from django.test.runner import DiscoverRunner
from unittest.suite import TestSuite
from django.test import TransactionTestCase

class UnitTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        pass
    def teardown_databases(self, old_config, **kwargs):
        pass
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        suite = super().build_suite(**kwargs)
        tests = [t for t in suite._tests if self.is_unittest(t)]
        return TestSuite(tests=tests)
    def is_unittest(self, test):
        return not issubclass(test.__class__, TransactionTestCase)
