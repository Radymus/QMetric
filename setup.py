#-*- coding: utf-8 -*-
"""
Created on Tue Apr  1 20:30:40 2014

@author: Radim Spigel
"""

from setuptools import setup

version_string = '0.0.1'

setup_kwargs = {
    'name': 'QMetric',
    'description': 'Evaluation the hypothetical quality for python projects. ',
    'keywords': 'git quality python gittle',
    'version': version_string,
    #'url': 'https://github.com/Radymus/QMetric',
    #'license': '',
    'author': "Radim Spigel",
    'author_email': 'radim.spigel@gmail.com',
    'long_description': """
    This is project is for evaluate the hypothetical quality of \
    the projects written in python.
    """,
    #'packages': ['QMetric'],
    'scripts':['QMetric.py'],
    'install_requires': [
    # PyPI
    'gittle==0.2.2',
    'dulwich==0.9.4',
   # 'gittle',
   # 'dulwich'
    ],
  #  'dependency_links': [
   #     'https://github.com/AaronO/dulwich/tarball/eebb032b2b7b982d21d636ac50b6e45de58b208b#egg=dulwich-0.9.4',
   # ],
}
setup(**setup_kwargs)
