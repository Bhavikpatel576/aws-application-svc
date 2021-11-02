from django.core.management.base import BaseCommand

from pylint.lint import Run
# from pylama.main import check_path, parse_options

ERROR_COUNT = 5
CONVENTION_COUNT = 5
WARNINGS = 5
CODEBASE = './src/'
THRESHOLD_LINT_SCORE = 9.5


class Command(BaseCommand):

    def run_pylint(self, path):

        results = Run(['--load-plugins=pylint_django',
                       '--rcfile=pylintrc_test_cases', path], do_exit=False)
        if results.linter.stats['error'] > ERROR_COUNT or results.linter.stats['convention'] > CONVENTION_COUNT or \
                results.linter.stats['warning'] > WARNINGS:
            print("Codebase has failed set standards, Please correct above mentioned issues,"
                  "Current Score is: %s, Errors: %s, Convention issues: %s, Warnings: %s" % (
                      results.linter.stats['global_note'], results.linter.stats['error'], results.linter.stats['convention'],
                      results.linter.stats['warning']))

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        """
        Overriden get handler method, call run_pylint for static analysis of code
        """
        self.run_pylint(options.get('path', CODEBASE))
