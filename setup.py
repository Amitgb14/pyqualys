# -*- coding: utf-8 -*-
import io
import os
import re

from setuptools import setup, find_packages


def read_version():
    """
    Read __version__ out of pyqualys/__init__.py without importing it.

    Importing the package would pull in requests, which is absent from
    an isolated PEP 517 build environment, so no sdist or wheel could
    ever be built.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(here, 'pyqualys', '__init__.py')
    with io.open(path, encoding='utf-8') as handle:
        source = handle.read()
    match = re.search(r"""^__version__\s*=\s*['"]([^'"]+)['"]""",
                      source, re.M)
    if not match:
        raise RuntimeError('Cannot find __version__ in %s' % path)
    return match.group(1)


def read_long_description():
    """Read README.md for the PyPI project page."""
    here = os.path.abspath(os.path.dirname(__file__))
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as handle:
        return handle.read()


VERSION = read_version()

setup(name='pyqualys',
      version=VERSION,
      description="Qualys's python API client library.",
      long_description=read_long_description(),
      long_description_content_type='text/markdown',
      url='https://github.com/Amitgb14/pyqualys',
      project_urls={
          'Source': 'https://github.com/Amitgb14/pyqualys',
          'Issues': 'https://github.com/Amitgb14/pyqualys/issues',
      },
      author='Amit Ghadge',
      author_email='amitg.b14@gmail.com',
      license='MIT',
      python_requires='>=3.7',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'License :: OSI Approved :: MIT License',
          'Topic :: Security',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'Programming Language :: Python :: 3.13',
      ],
      install_requires=['lxml>=4.1.1',
                        'requests>=2.18.1',
                        'simplejson>=3.15.0'],
      # No python_version marker on purpose: with one, `pip install
      # pyqualys[mcp]` on 3.9 would silently install nothing.
      extras_require={'mcp': ['mcp>=1.27,<2']},
      entry_points={
          'console_scripts': [
              'pyqualys-mcp = pyqualys.mcp.server:main',
          ],
      }
      )
