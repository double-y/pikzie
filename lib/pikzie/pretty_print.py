import re
import types
import pprint

def format(object):
    return pprint.pformat(object)

_re_class = type(re.compile(""))
def _re_flags(pattern):
    result = ""
    if isinstance(pattern, _re_class):
        if pattern.flags & re.IGNORECASE: result += "i"
        if pattern.flags & re.LOCALE: result += "l"
        if pattern.flags & re.MULTILINE: result += "m"
        if pattern.flags & re.DOTALL: result += "d"
        if pattern.flags & re.UNICODE: result += "u"
        if pattern.flags & re.VERBOSE: result += "x"
    return result

def _re_flags_repr(pattern):
    flags = []
    if isinstance(pattern, _re_class):
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

def format_re(pattern):
    re_flags = _re_flags(pattern)
    if hasattr(pattern, "pattern"):
        pattern = pattern.pattern
    pattern = format(pattern)
    return "/%s/%s" % (pattern[1:-1], re_flags)

def format_re_repr(pattern):
    re_flags_repr = _re_flags_repr(pattern)
    if hasattr(pattern, "pattern"):
        pattern = pattern.pattern
    pattern = pprint.pformat(pattern)
    if re_flags_repr:
        return "re.compile(%s, %s)" % (pattern, re_flags_repr)
    else:
        return pattern

def format_callable_object(callable_object):
    if hasattr(callable_object, "im_class"):
        cls = callable_object.im_class
        return "%s.%s.%s" % (cls.__module__,
                             cls.__class__.__name__,
                             callable_object.__name__)
    else:
        return "%s.%s" % (callable_object.__module__,
                          callable_object.__name__)

def format_call_arguments(args, kw_args):
    formatted_args = map(lambda arg: format(arg), args)
    formatted_args.extend(["%s=%s" % (format(key), format(value))
                           for (key, value) in kw_args.items()])
    return ", ".join(formatted_args)

def format_call(callable_object, args, kw_args):
    return "%s(%s)" % (format_callable_object(callable_object),
                       format_call_arguments(args, kw_args))

def format_exception_class(exception_class):
    if issubclass(exception_class, Exception) or \
            issubclass(exception_class, types.ClassType):
        return str(exception_class)
    else:
        return format(exception_class)

