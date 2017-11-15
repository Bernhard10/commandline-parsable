"""
In addition to test.py, this tests extra features only available on python 3
"""

import argparse
import textwrap
import sys
import logging

from commandline_parsable import parsable_base

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

@parsable_base(base_instantiable=True, factory_function="create")
class ClassA(object):
    """
    This is the Base-Class
    """
    @classmethod
    def create(cls, arg1 :int):
        instance = cls()
        instance.arg1 = arg1
        return instance

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

def test_argument_is_converted():
    log.error("Getting instances")
    instances = ClassA.from_string("ClassD[12],ClassB[15]")
    log.error("Done")
    assert instances[0].arg1 == 12
    assert isinstance(instances[0].arg1, int)

def test_argument_conversion_error():
    """
    If a conversion does not work, we pass the unconverted string (like in python2)
    """
    instances = ClassA.from_string("ClassD[12.4]")
    assert isinstance(instances[0].arg1, str)
