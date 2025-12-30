from setuptools import setup

setup(name='cbpi4-ButtonController',
      version='0.1.0',
      description='CraftBeerPi GPIO Button Plugin',
      author='Jan Homann',
      author_email='',
      url='https://github.com/WeaselDev/cbpi4-ButtonController',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-ButtonController': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4_ButtonController'],
     )
