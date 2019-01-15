import inspect
import logging
import regex as re
import traceback
import sys

if sys.version_info[0] >2:
    PY3K=True
else:
    PY3K=False
    import six

from collections import OrderedDict
log=logging.getLogger(__name__)


def _get_all_subclasses(cls, include_base = False):
    """
    Get all subclasses of a given class, unless they are abstract.

    Code modified from http://stackoverflow.com/a/17246726/5069869 by fletom
    """
    all_subclasses = []
    if include_base:
        if inspect.isabstract(cls):
            log.warning("BaseClass %s is abstract and will not be included "
                        "in the list of all subclasses.", cls)
        else:
            log.debug("Including base-class %s", cls)
            all_subclasses.append(cls)

    for subclass in cls.__subclasses__():
        if inspect.isabstract(subclass):
            log.debug("Not including abstract sub-class %s, but searching recursively.", subclass)
        else:
            log.debug("Including sub-class %s and searching recursively.", subclass)
            all_subclasses.append(subclass)
        all_subclasses.extend(_get_all_subclasses(subclass))
        log.debug("Search for subsubclasses (subclasses of %s) done", subclass)
    return all_subclasses


def _try_convert(value, target_type):
    try:
        log.debug("Trying to convert argument %s to %s", value, target_type)
        return target_type(value)
    except:
        log.warning("Could not convert argument %s to %s", value, target_type)
        return value


def _convert_and_call(function, *args, **kwargs):
    """
    Use annotation to convert args and kwargs to the correct type before calling function

    If __annotations__ is not present (py2k) or empty, do not perform any conversion.

    This tries to perform the conversion by calling the type (works for int,str).
    If calling the type results in an error, no conversion is performed.
    """
    args = list(args)
    if PY3K:
        argspec = inspect.getfullargspec(function)
        annot = argspec.annotations
        log.debug("Function's annotations are: %s", annot)
        for i, arg in enumerate(argspec.args):
            i=i-1 # cls/ self does not count
            if arg in annot:
                log.debug("For arg %s: i=%s, args=%s", arg, i, args)
                if i<len(args):
                    args[i]=_try_convert(args[i], annot[arg])
                elif arg in kwargs:
                    kwargs[arg]=_try_convert(kwargs[arg], annot[arg])
            else:
                log.debug("No annotation present for %s", arg)
    log.debug("Calling %s with args=%s, kwargs=%s", function.__name__, args, kwargs)
    return function(*args, **kwargs)


def call(function, *args, **kwargs):
    try:
        return _convert_and_call(function, *args, **kwargs)
    except TypeError as e:
        if "argument" not in str(e):
            raise
        t, v, tb = sys.exc_info()
        log.error("Error calling %s", function.__name__)
        log.exception("The following exception occured and will be reraised with a potentially different message:")
        log.error(" ")
        try:
            log.debug("Getting rgspec of function")
            argspec = inspect.getargspec(function)
            target_args = argspec.args
        except TypeError:
            try:
                log.debug("getting argspec of init")
                argspec = inspect.getargspec(function.__init__)
            except TypeError as e2:
                log.debug("Cannot get argspec: %s", e2)
                if PY3K:
                    raise e #from None
                else:
                    # Reraise original error
                    six.reraise(t, v, tb)
            target_args = argspec.args[1:]

        target_kwargs = target_args[len(args)+1:]
        missing_args = set(target_kwargs) - set(kwargs.keys())
        tb = traceback.extract_tb(sys.exc_info()[2])
        signature = ", ".join(argspec.args)
        if argspec.varargs:
            signature+=", *{}".format(argspec.varargs)
        if argspec.keywords:
            signature+=", **{}".format(argspec.keywords)
        used_sig = ", ".join(map(repr,args))+", "*(bool(args) and bool(kwargs))+", ".join("{}={}".format(k,v) for k,v in kwargs.items())
        if tb[-1][2] == "_convert_and_call":
            try:
               fname = function.__qualname__
            except AttributeError:
               try:
                  if function.im_self is not None: # bound method
                      fname = function.im_self.__name__ + "." + function.__name__
                  else:
                      fname = function.im_class.__name__ + "." + function.__name__
               except Exception as ex2:
                  # py 3.0-3.2
                  fname = function.__name__
            msg = (str(e) + "\nTried to call {fun} with signature ({target_sig}) (from module"
                           " {module}) as {fun}({used_sig}) "
                           "".format(fun=fname,
                                     target_sig = signature,
                                     module=function.__module__,
                                     used_sig=used_sig
                                    ))
            if missing_args:
                msg+=("The following arguments are "
                      "missing: {}".format(list(missing_args)))
            raise TypeError(msg)
        else:
            raise

def split_by_outerlevel_character(string, character=","):
    """
    Thanks to Wiktor Stribizew at stackoverflow: https://stackoverflow.com/a/36327468
    """
    if string.count("[") != string.count("]"):
           raise ValueError("Unbalanced brackets encountered.")
    regex = r"(?P<nested>\[(?:[^\[\]]++|(?&nested))*\])(*SKIP)(*FAIL)|[{0}]+".format(re.escape(character))
    fields = re.split(regex, string)
    return [ f for f in fields if f ]

def format_helpentry(name, text):
    lines = text.splitlines()
    help_txt = "`{}`: {}\n".format(name, lines.pop(0))
    indent=len(name)
    if indent>15:
        indent=10
    indent=" "*max(3,indent)
    for line in lines:
        help_txt += " {}   {}\n".format(indent, line)
    return help_txt[:-1]

def parsable_base(base_instantiable=True, required_kwargs = [],
                  factory_function = None, name_attr=None, helptext_sep=", ",
                  help_attr="__doc__", allow_pre_and_post_number=False,
                  help_intro_list_sep=". One of the following: "):
    """
    A class decorator that adds the `from_string` factory classmethod to a class

    :param base_instantiable: Whether or not instances of the base-class
                              can be instantiated.
    :param required_kwargs:

    """
    if factory_function in ["from_string", "add_to_parser"]:
        raise ValueError("The name {} is reserved by parsable_base and cannot be used as factory_function.".format(factory_function))

    def _get_helptext(cls, intro):
        help_txt = intro+help_intro_list_sep
        help_txt += helptext_sep.join(
                        format_helpentry(name, getattr(c, help_attr).strip())
                        for name, c in _subclass_dict(cls).items()
                   )
        return help_txt
    def _subclass_dict(cls):
        subclasses = _get_all_subclasses(cls, base_instantiable)
        cls_dict = OrderedDict()
        for subcls in subclasses:
            if name_attr is None:
                name = subcls.__name__
            else:
                name = getattr(subcls, name_attr)
            cls_dict[name] = subcls
        return cls_dict

    def add_to_parser(cls, parser, arg_name, help_intro="", default=None):
        if default is not None:
            kwargs={"default":default}
        else:
            kwargs={}
        parser.add_argument(arg_name,
                            help=_get_helptext(cls, help_intro),
                            type=str, action="store", **kwargs )

    def from_string(cls, string, *args, **kwargs):
        """
        Create a list of instances of (subclasses of) this class based on string.

        :param string: This is typically received as commandline argument.
        """
        if args:
            raise TypeError("from_string() takes exactly 2 arguments ({} given)."
                            " Please specify all arguments "
                            "(except cls and string) as keyword arguments.".format(len(args)+2))
        log.debug("from_string called with kwargs: %s. Required kwargs are: %s", set(kwargs.keys()), set(required_kwargs))
        if not (set(kwargs.keys()) >= set(required_kwargs)):
            missing = set(required_kwargs) - set(kwargs.keys())
            extra   = set(kwargs.keys())-set(required_kwargs)
            extra_info = ""
            if missing:
                extra_info+="\nMissing: {}; ".format(", ".join(missing))
            if extra:
                extra_info+="\nExtra argument(s): {}".format(", ".join(extra))
            raise TypeError("from_string of class {} requires the following "
                            "keyword arguments: {}.{}".format(cls.__name__,
                                                              ", ".join(required_kwargs),
                                                              extra_info))
        if string.count("[") != string.count("]"):
            raise ValueError("Unbalanced Brackets: Found {} times `[` but "
                             "{} times `]`".format(string.count("["),string.count("]")))
        if allow_pre_and_post_number:
            regex = r"(?P<pre>(?:-?[0-9]*\.?[0-9]+_?)*)(?P<name>[a-zA-Z][a-zA-Z_]*)(?P<post>(?:-?[0-9]*\.?[0-9]+_?)*)(?P<arguments>(?:\[(?:.*?(?&arguments).*?)*?\])?)"
        else:
            regex =r"(?P<name>[0-9a-zA-Z_]+)(?P<arguments>(?:\[(?:.*?(?&arguments).*?)*?\])?)"
        matches = [ mo for mo in re.finditer(regex, string)]
        whole_match = ",".join(mo.group(0) for mo in matches)
        if whole_match != string:
            for i in range(len(whole_match)):
                try:
                    if whole_match[i]!=string[i]:
                        char = string[i]
                        raise ValueError("'{}' not understood. Unexpected character at pos {}: '{}', expected '{}'".format(string, i, char, whole_match[i]))
                except KeyError:
                    pass
            raise ValueError("'{}' not understood. Error after pos {}: '...{}'".format(string, i, whole_match[i-5:i-1]))

        subclasses = _subclass_dict(cls)

        return_instances = []
        log.debug("Matches are %s", matches)
        for mo in matches:
            #import pdb; pdb.set_trace()
            try:
                target_cls = subclasses[mo.group("name")]
            except KeyError as e:
                raise ValueError("Unknown subclass of class {}: '{}'.\n"
                                 "Valid names are: {}".format(cls.__name__, e,
                                                            subclasses.keys()))
            if factory_function:
                instantiate = getattr(target_cls, factory_function)
            else:
                instantiate = target_cls
            arguments = mo.group("arguments")
            if arguments:
                assert arguments[0]=="[" and arguments[-1]=="]"
                arguments = arguments[1:-1]
                arguments = split_by_outerlevel_character(arguments, ",")
            else:
                arguments = []

            if allow_pre_and_post_number:
                pre = mo.group("pre")
                post = mo.group("post")
                instance = call(instantiate, pre, post, *arguments, **kwargs)
            else:
                instance = call(instantiate, *arguments, **kwargs)
            return_instances.append(instance)
        return return_instances

    def decorate(cls):
        cls.add_to_parser=classmethod(add_to_parser)
        if required_kwargs:
            from_string.__doc__+="\nThe following keyword arguments are required: {}".format(", ".join(required_kwargs))
        cls.from_string=classmethod(from_string)
        return cls
    return decorate
