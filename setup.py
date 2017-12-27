from os import path

from setuptools import setup, find_packages


def get_long_description():
    readme_path = path.join(path.abspath(path.dirname(__file__)), 'README.md')
    with open(readme_path, encoding='utf-8') as readme:
        return readme.read()


setup(
    name='wasm-forth',
    version='1.0.0',
    author='Stefano Dissegna',
    description='A Forth implementation compiling to WebAssembly.',
    long_description=get_long_description(),
    url='https://github.com/stefano/wasm-forth/',
    license='GPLv3',
    keywords='forth wasm WebAssembly compiler interpreter',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Interpreters',
    ],
    packages=find_packages(),
    setup_requires=['cffi>=1.0.0'],
    cffi_modules=['kernel/build_binaryen_ext.py:ffibuilder'],
    install_requires=['cffi>=1.0.0'],
)
