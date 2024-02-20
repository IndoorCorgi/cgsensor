from setuptools import setup

setup(
    name='cgsensor',
    version='1.1',
    description='Python package and command line tool to control sensors on Raspberry Pi',
    author='Indoor Corgi',
    author_email='indoorcorgi@gmail.com',
    url='https://github.com/IndoorCorgi/cgsensor',
    license='Apache License 2.0',
    packages=['cgsensor'],
    install_requires=['docopt', 'smbus2'],
    entry_points={'console_scripts': ['cgsensor=cgsensor:cli',]},
    python_requires='>=3.6',
)
