from django.contrib.staticfiles.management.commands.runserver import Command as StaticfilesRunserverCommand

from pylint.lint import Run
# from pylama.main import check_path, parse_options

ERROR_COUNT = 5
CONVENTION_COUNT = 5
WARNINGS = 5
CODEBASE = './src/'
THRESHOLD_LINT_SCORE = 9.5


class Command(StaticfilesRunserverCommand):

    def run_pylint(self):
        results = Run(['--load-plugins=pylint_django',
                       '--rcfile=pylintrc', CODEBASE], do_exit=False)
        if results.linter.stats['error'] > ERROR_COUNT or results.linter.stats['convention'] > CONVENTION_COUNT or \
                results.linter.stats['warning'] > WARNINGS:
            print("Codebase has failed set standards, Please correct above mentioned issues,"
                  "Current Score is: %s, Errors: %s, Convention issues: %s, Warnings: %s" % (
                      results.linter.stats['global_note'], results.linter.stats['error'], results.linter.stats['convention'],
                      results.linter.stats['warning']))

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

    def get_handler(self, *args, **options):
        """Overriden get handler method, call run_pylint for static analysis of code
        """
        handler = super(Command, self).get_handler(*args, **options)
        self.run_pylint()
        return handler
