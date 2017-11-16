import inspect
import logging
import re

from collections import OrderedDict
log=logging.getLogger(__name__)


def _get_all_subclasses(cls, include_base = False):
    """
    Thanks to fletom at http://stackoverflow.com/a/17246726/5069869
    """
    all_subclasses = []
    if include_base:
        log.debug("Including base-class %s", cls)
        all_subclasses.append(cls)

    for subclass in cls.__subclasses__():
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
    try:
        argspec = inspect.getfullargspec(function)
    except AttributeError:
        pass # Py2K
    else:
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
    return function(*args, **kwargs)


def call(function, *args, **kwargs):
    try:
        return _convert_and_call(function, *args, **kwargs)
    except TypeError as e:
        if "arguments" not in str(e):
            raise
        argspec = inspect.getfullargspec(function)
        target_kwargs = argspec.args[len(args):]
        missing_arg = set(target_kwargs)-set(kwargs.keys())
        if missing_arg:
            raise TypeError(*e.args, " The following required arguments are "
                            "missing: {}".format(function, missing_arg))
        else:
            raise


def parsable_base(base_instantiable=True, required_kwargs = [],
                  factory_function = None, name_attr=None, helptext_sep=", ",
                  help_attr="__doc__", allow_pre_and_post_number=False,
                  help_intro_list_sep=". One of the following: "):
    """
    A class decorator that adds the `from_string` factory classmethod to a class

    :param base_instantiable: Whether or not instances of the base-class can be instantiated.

    """
    if factory_function in ["from_string", "add_to_parser"]:
        raise ValueError("The name {} is reserved by parsable_base and cannot be used as factory_function.".format(factory_function))

    def _get_helptext(cls, intro):
        help_txt = intro+help_intro_list_sep
        help_txt += helptext_sep.join(
                        "`{}`: {}".format(name, getattr(c, help_attr).strip())
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
            kwargs={default:default}
        else:
            kwargs={}
        parser.add_argument(arg_name,
                            help=_get_helptext(cls, help_intro),
                            type=str, nargs=1, **kwargs )

    def from_string(cls, string, **kwargs):
        """
        Create a list of instances of (subclasses of) this class based on string.

        :param string: This is typically received as commandline argument.
        """
        if set(kwargs.keys()) != set(required_kwargs):
            try:
                missing = set(required_kwargs) - kwargs.keys()
                extra   = kwargs.keys()-set(required_kwargs)
            except TypeError: #Python 2
                extra_info = ""
            else:
                extra_info = ("Missing arguments: {}, "
                              "extra arguments: {}".format(missing, extra))
            raise TypeError("from_string of class {} requires the following "
                            "keyword arguments: {}.{}".format(cls.__name__,
                                                              required_kwargs,
                                                              extra_info))
        if allow_pre_and_post_number:
            regex = r"(?P<pre>(?:-?[0-9]*\.?[0-9]+_?)*)(?P<name>[a-zA-Z][a-zA-Z_]*)(?P<arguments>(?:\[.*?\])*)(?P<post>(?:-?[0-9]*\.?[0-9]+_?)*)"
        else:
            regex =r"(?P<name>[0-9a-zA-Z_]+)(?P<arguments>(?:\[.*?\])*)"
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
                arguments = arguments[1:-1].split(",")
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
