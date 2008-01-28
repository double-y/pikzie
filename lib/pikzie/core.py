import pprint
import re
import sys
import traceback
import os
import glob
import types
import time
import pprint

from pikzie.color import *
from pikzie.faults import *
from pikzie.assertions import Assertions

__all__ = ["TestSuite", "TestCase", "TestResult", "TestLoader"]

class TestSuite(object):
    """A test suite is a composite test consisting of a number of TestCases.

    For use, create an instance of TestSuite, then add test case instances.
    When all tests have been added, the suite can be passed to a test
    runner, such as TextTestRunner. It will run the individual test cases
    in the order in which they were added, aggregating the results. When
    subclassing, do not forget to call the base class constructor.
    """
    def __init__(self, tests=()):
        self._tests = []
        self.add_tests(tests)

    def __iter__(self):
        return iter(self._tests)

    def __len__(self):
        return sum(map(len, self._tests))

    def add_test(self, test):
        self._tests.append(test)

    def add_tests(self, tests):
        for test in tests:
            self.add_test(test)

    def run(self, result):
        for test in self._tests:
            test.run(result)
            if result.need_interrupt():
                break

class Traceback(object):
    def __init__(self, filename, lineno, name, line):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self.line = line

    def __str__(self):
        result = '%s:%d: %s()' % (self.filename, self.lineno, self.name)
        if self.line:
            result = "%s: %s" % (result, self.line)
        return result

class AssertionFailure(Exception):
    def __init__(self, message, user_message=None):
        self.message = message
        self.user_message = user_message

    def __str__(self):
        result = self.message
        if self.user_message:
            result += self.user_message + "\n"
        return result

class TestCaseTemplate(object):
    def setup(self):
        "Hook method for setting up the test fixture before exercising it."
        pass

    def teardown(self):
        "Hook method for deconstructing the test fixture after testing it."
        pass

class TestCase(TestCaseTemplate, Assertions):
    """A class whose instances are single test cases.

    By default, the test code itself should be placed in a method named
    'runTest'.

    If the fixture may be used for many test cases, create as
    many test methods as are needed. When instantiating such a TestCase
    subclass, specify in the constructor arguments the name of the test method
    that the instance is to execute.

    Test authors should subclass TestCase for their own tests. Construction
    and deconstruction of the test's environment ('fixture') can be
    implemented by overriding the 'setUp' and 'tearDown' methods respectively.

    If it is necessary to override the __init__ method, the base class
    __init__ method must always be called. It is important that subclasses
    should not change the signature of their __init__ method, since instances
    of the classes are instantiated automatically by parts of the framework
    in order to be run.
    """

    def __init__(self, method_name):
        self.__method_name = method_name
        self.__description = getattr(self, method_name).__doc__

    def __len__(self):
        return 1

    def description(self):
        """Returns a one-line description of the test, or None if no
        description has been provided.

        The default implementation of this method returns the first line of
        the specified test method's docstring.
        """
        description = self.__description
        if description:
            return description.split("\n")[0].strip()
        else:
            return None

    def id(self):
        return "%s.%s.%s" % (self.__class__.__module__,
                             self.__class__.__name__,
                             self.__method_name)

    def __str__(self):
        return "%s.%s" % (self.__class__.__name__, self.__method_name)

    def __repr__(self):
        return "<%s method_name=%s description=%s>" % \
               (str(self.__class__), self.__method_name, self.__description)

    def run(self, result):
        try:
            self.__result = result
            result.start_test(self)

            success = False
            try:
                try:
                    self.setup()
                except KeyboardInterrupt:
                    result.interrupted()
                    return
                except:
                    self._add_error(result)
                    return

                try:
                    getattr(self, self.__method_name)()
                    success = True
                except AssertionFailure:
                    self._add_failure(result)
                except KeyboardInterrupt:
                    result.interrupted()
                    return
                except:
                    self._add_error(result)
            finally:
                try:
                    self.teardown()
                except KeyboardInterrupt:
                    result.interrupted()
                except:
                    self._add_error(result)
                    success = False

            if success:
                result.add_success(self)
        finally:
            result.stop_test(self)
            self.__result = None

    def _pass_assertion(self):
        self.__result.pass_assertion(self)

    def _fail(self, message, user_message=None):
        raise AssertionFailure(message, user_message)

    def _pformat_exception_class(self, exception_class):
        if issubclass(exception_class, Exception) or \
                issubclass(exception_class, types.ClassType):
            return str(exception_class)
        else:
            return pprint.pformat(exception_class)

    def _pformat_re(self, pattern):
        re_flags = self._re_flags(pattern)
        if hasattr(pattern, "pattern"):
            pattern = pattern.pattern
        pattern = pprint.pformat(pattern)
        return "/%s/%s" % (pattern[1:-1], re_flags)

    def _pformat_re_repr(self, pattern):
        re_flags_repr = self._re_flags_repr(pattern)
        if hasattr(pattern, "pattern"):
            pattern = pattern.pattern
        pattern = pprint.pformat(pattern)
        if re_flags_repr:
            return "re.compile(%s, %s)" % (pattern, re_flags_repr)
        else:
            return pattern

    _re_class = type(re.compile(""))
    def _re_flags(self, pattern):
        result = ""
        if isinstance(pattern, self._re_class):
            if pattern.flags & re.IGNORECASE: result += "i"
            if pattern.flags & re.LOCALE: result += "l"
            if pattern.flags & re.MULTILINE: result += "m"
            if pattern.flags & re.DOTALL: result += "d"
            if pattern.flags & re.UNICODE: result += "u"
            if pattern.flags & re.VERBOSE: result += "x"
        return result

    def _re_flags_repr(self, pattern):
        flags = []
        if isinstance(pattern, self._re_class):
            if pattern.flags & re.IGNORECASE: flags.append("re.IGNORECASE")
            if pattern.flags & re.LOCALE: flags.append("re.LOCALE")
            if pattern.flags & re.MULTILINE: flags.append("re.MULTILINE")
            if pattern.flags & re.DOTALL: flags.append("re.DOTALL")
            if pattern.flags & re.UNICODE: flags.append("re.UNICODE")
            if pattern.flags & re.VERBOSE: flags.append("re.VERBOSE")
        if len(flags) == 0:
            return None
        else:
            return " | ".join(flags)

    def _add_failure(self, result):
        exception_type, detail, traceback = sys.exc_info()
        tracebacks = self._prepare_traceback(traceback, True)
        failure = Failure(self, detail, tracebacks)
        result.add_error(self, failure)

    def _add_error(self, result):
        exception_type, detail, traceback = sys.exc_info()
        tracebacks = self._prepare_traceback(traceback, False)
        error = Error(self, exception_type, detail, tracebacks)
        result.add_error(self, error)

    def _prepare_traceback(self, tb, compute_length):
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next
        length = None
        if compute_length:
            length = self._count_relevant_tb_levels(tb)
        tracebacks = []
        for tb in traceback.extract_tb(tb, length):
            filename, lineno, name, line = tb
            tracebacks.append(Traceback(filename, lineno, name, line))
        return tracebacks

    def _is_relevant_tb_level(self, tb):
        globals = tb.tb_frame.f_globals
        for cls in (TestCase,) + TestCase.__bases__:
            name = cls.__name__
            if globals.has_key(name) and globals[name] == cls:
                return True
        return False

    def _count_relevant_tb_levels(self, tb):
        length = 0
        while tb and not self._is_relevant_tb_level(tb):
            length += 1
            tb = tb.tb_next
        return length


class TestLoader(object):
    def __init__(self, pattern=None, test_name=None, test_case_name=None):
        if pattern is None:
            pattern = "**/test_*.py"
        self.pattern = pattern
        self.test_name = test_name
        self.test_case_name = test_case_name

    def find_targets(self):
        targets = []
        for target in glob.glob(self.pattern):
            if os.path.isfile(target):
                targets.append(target)
        return targets

    def load_modules(self):
        modules = []
        for target in self.find_targets():
            target = os.path.splitext(target)[0]
            target = re.sub(re.escape(os.path.sep), ".", target)
            parts = target.split(".")
            module = None
            while len(parts) > 0 and module is None:
                try:
                    name = ".".join(parts)
                    __import__(name)
                    module = sys.modules[name]
                except ImportError:
                    pass
                parts.pop()
            if module is not None:
                modules.append(module)
        return modules

    def collect_test_cases(self):
        test_cases = []
        for module in self.load_modules():
            for name in dir(module):
                object = getattr(module, name)
                if (isinstance(object, (type, types.ClassType)) and
                    issubclass(object, TestCase)):
                    test_cases.append(object)
        return test_cases

    def create_test_suite(self):
        tests = []
        for test_case in self.collect_test_cases():
            def is_test_method(name):
                return name.startswith("test_") and \
                    callable(getattr(test_case, name))
            tests.extend(map(test_case, filter(is_test_method, dir(test_case))))
        return TestSuite(tests)

class TestResult(object):
    """Holder for test result information.

    Test results are automatically managed by the TestCase and TestSuite
    classes, and do not need to be explicitly manipulated by writers of tests.

    Each instance holds the total number of tests run, and collections of
    failures and errors that occurred among those test runs. The collections
    contain tuples of (testcase, exceptioninfo), where exceptioninfo is the
    formatted traceback of the error that occurred.
    """
    def __init__(self):
        self.n_assertions = 0
        self.n_tests = 0
        self.faults = []
        self.listners = []
        self.interrupted = False
        self.elapsed = 0

    def add_listner(self, listener):
        self.listners.append(listener)

    def n_faults(self):
        return len(self.faults)
    n_faults = property(n_faults)

    def n_failures(self):
        return len(filter(lambda fault: isinstance(fault, Failure), self.faults))
    n_failures = property(n_failures)

    def n_errors(self):
        return len(filter(lambda fault: isinstance(fault, Error), self.faults))
    n_errors = property(n_errors)

    def pass_assertion(self, test):
        self.n_assertions += 1
        self._notify("pass_assertion", test)

    def start_test(self, test):
        "Called when the given test is about to be run"
        self._start_at = time.time()
        self.n_tests += 1
        self._notify("start_test", test)

    def stop_test(self, test):
        "Called when the given test has been run"
        self._stop_at = time.time()
        self.elapsed += (self._stop_at - self._start_at)

    def add_error(self, test, error):
        """Called when an error has occurred."""
        self.faults.append(error)
        self._notify("error", error)

    def add_failure(self, test, failure):
        """Called when a failure has occurred."""
        self.faults.append(failure)
        self._notify("failure", failure)

    def add_success(self, test):
        "Called when a test has completed successfully"
        self._notify("success", test)

    def interrupt(self):
        "Indicates that the tests should be interrupted"
        self.interrupted = True

    def need_interrupt(self):
        return self.interrupted

    def succeeded(self):
        return len(self.faults) == 0

    def _notify(self, name, *args):
        for listner in self.listners:
            callback_name = "on_%s" % name
            if hasattr(listner, callback_name):
                getattr(listner, callback_name)(self, *args)

    def summary(self):
        return "%d test(s), %d assertion(s), %d failure(s), %d error(s)" % \
            (self.n_tests, self.n_assertions, self.n_failures, self.n_errors)

    __str__ = summary