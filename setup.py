# -*- coding: utf-8 -*-
"""
Real Time Audio setup file.

Authors:
    João Vitor Gutkoski Paes, joaovitorgpaes@gmail.com

"""

from setuptools import setup


with open("README.md", "r") as f:
    long_description = f.read()


settings = {
    'name': 'realtimesound',
    'version': '0.1.0a',
    'description': ('Data visualization in real time for '
                    + 'PortAudio streams using multiprocessing.'),
    'long_description': long_description,
    'long_description_content_type': 'text/markdown',
    'url': 'http://github.com/Chum4k3r/RealTimeSound',
    'author': 'João Vitor G. Paes',
    'author_email': 'joaovitorgpaes@gmail.com',
    'license': 'MIT',
    'install_requires': ['numpy', 'sounddevice'],
    'classifiers': [
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent", ],
    'python_requires': '>=3.6',
}


setup(**settings)
