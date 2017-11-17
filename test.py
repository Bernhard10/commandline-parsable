import argparse
import textwrap
import sys
from commandline_parsable import parsable_base
from commandline_parsable import split_by_outerlevel_character as resplit

@parsable_base(base_instantiable=True, required_kwargs=["hallo"], factory_function=None,)
class ClassA(object):
    """
    This is the Base-Class
    """
    def __init__(self, hallo):
        self._hallo = hallo

class ClassB(ClassA):
    """
    The is B-B-B-Better
    """
    pass

class ClassC(ClassA):
    """
    The C-C-C-C-classical option
    """
    pass

class ClassD(ClassB):
    """
    This is D-D-D-D-delicate
    """
    pass


@parsable_base(base_instantiable=True, factory_function="build")
class AnotherClass(object):
    """
    This is another Base-Class
    """
    @classmethod
    def build(cls, arg1, arg2):
        instance = cls()
        instance.arg1 = arg1
        instance.arg2 = arg2
        return instance

class AnotherSubClass(AnotherClass):
    """
    This is another Sub-Class
    """
    @classmethod
    def build(cls, arg1, arg2, arg3):
        instance = cls()
        instance.arg1 = arg1
        instance.arg2 = arg2
        instance.arg3 = arg3
        return instance

def test_helpmessage():
    parser = argparse.ArgumentParser(prog="EXECUTABLE", formatter_class=argparse.RawTextHelpFormatter)
    ClassA.add_to_parser(parser, "--option1", "Choose the class you like to use")
    helpmessage = parser.format_help()
    expectedHelp =  """\
                        usage: EXECUTABLE [-h] [--option1 OPTION1]

                        optional arguments:
                          -h, --help         show this help message and exit
                          --option1 OPTION1  Choose the class you like to use. One of the following: `ClassA`: This is the Base-Class, `ClassB`: The is B-B-B-Better, `ClassD`: This is D-D-D-D-delicate, `ClassC`: The C-C-C-C-classical option                    """
    assert helpmessage.strip() == textwrap.dedent(expectedHelp).strip()

def test_correct_class_instantiated():
    instances = ClassA.from_string("ClassD", hallo=12)
    assert type(instances[0]) ==  ClassD
    assert instances[0]._hallo == 12

def test_correct_class_instantiated_multiple():
    instances = ClassA.from_string("ClassD,ClassB", hallo=12)
    assert type(instances[0]) == ClassD
    assert type(instances[1]) == ClassB

def test_nested_arguments():
    instances = AnotherClass.from_string("AnotherClass[aaa[b],bbb],AnotherSubClass[cd[e[f,g,h],i]bla,gh[i],jkl]")
    assert instances[0].arg1 == "aaa[b]"
    assert instances[0].arg2 == "bbb"

    assert instances[1].arg1 == "cd[e[f,g,h],i]bla"
    assert instances[1].arg2 == "gh[i]"
    assert instances[1].arg3 == "jkl"

def test_split_by_outerlevel_character():
    assert resplit("a,[b,v[f],de[e,t[f,]]],www,2e2[323,2]", ",")==["a","[b,v[f],de[e,t[f,]]]", "www", "2e2[323,2]"]
    assert resplit("ab,cd[3,e.]..e,,f", ",.") == ["ab","cd[3,e.]","e","f"]
    assert resplit("ab[p,k]") == ["ab[p,k]"]
