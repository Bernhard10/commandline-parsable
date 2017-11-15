import argparse
import textwrap
import sys
from commandline_parsable import parsable_base

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
