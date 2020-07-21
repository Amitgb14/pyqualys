# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from pyqualys import __version__ as VERSION

setup(name='pyqualys',
      version=VERSION,
      description="Qualys's python API client library.",
      url='https://github.com/Amitgb14/pyqualys.git',
      author='Amit Ghadge',
      author_email='amitg.b14@gmail.com',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      install_requires=['lxml>=4.1.1',
                        'requests>=2.18.1',
                        'simplejson>=3.15.0']
      )
