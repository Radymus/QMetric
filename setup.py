#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
# Author: "Radim Spigel" <spigel@seznam.cz>

"""
Created on Tue Apr  1 20:30:40 2014

@author: Radim Spigel
"""

from setuptools import setup

version_string = '0.1.0'

description = (
    "This is project is for evaluate the hypothetical "
    "quality of the projects written in python.")

setup_kwargs = {
    'name': 'QMetric',
    'description': 'Evaluation the hypothetical quality for python projects. ',
    'keywords': ['git', 'quality', 'python', 'gittle'],
    'version': version_string,
    'url': 'https://github.com/Radymus/QMetric',
    'license': 'GPLv3',
    'author': "Radim Spigel",
    'author_email': 'radim.spigel@gmail.com',
    'long_description': description,
    'packages': [],
    'scripts': ['QMetric.py'],
    'install_requires': [
        'dulwich==0.9.4',
        'gittle==0.3.0',
        'pylint',
        'pandas',
        'jinja2',
        'funky',
        'lxml',
        'scipy',
        'matplotlib',
        'radon',
        'mpld3'
    ],
}
setup(**setup_kwargs)
