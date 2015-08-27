version = '0.2'
from setuptools import setup, find_packages

setup(
    name = 'Flask-SSI',
    version = version,
    license = 'MIT',
    author = 'Alexey Poryadin',
    author_email='alexey.poryadin@gmail.com',
    description='Flask extension to implement fragment caching',
    packages = ['flask_ssi'],
    install_requires = [
        'Flask',
    ],
)
