from setuptools import setup

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(name='jbang',
      version='0.2.0',
      description='Python for JBang - Java Script in your Python',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://jbang.dev',
      author='JBang Developers',
      author_email='team@jbang.dev',
      license='MIT',
      packages=['jbang'],
      zip_safe=False)