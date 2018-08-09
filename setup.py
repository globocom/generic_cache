from setuptools import setup

with open('README.md', 'r') as f:
    readme = f.read()

setup(name='generic_cache',
      version='0.0.1',
      description='A Python utility / library to facilitate caching functions results',
      long_description=readme,
      author='Pedro Celes',
      author_email='pedro.celes123@gmail.com',
      packages=['generic_cache'],
    )