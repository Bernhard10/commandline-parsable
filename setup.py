from setuptools import setup


setup(name='commandline_parsable',
      version='0.2.0',
      description='Choose subclass based on commandline options',
      author='Bernhard Thiel',
      author_email='thiel@tbi.univie.ac.at',
      url='https://github.com/Bernhard10/commandline-parsable',
      py_modules=["commandline_parsable"],
      install_requires=[
        "regex"]
     )
