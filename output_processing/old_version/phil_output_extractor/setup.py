
from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
        Extension(
            name = 'phil_output_extractor.count_events',
            sources = ['src/phil_output_extractor/count_events.pyx'],
            include_dirs = [np.get_include()],
            language = 'c',
            #library_dirs = ['/usr/local/lib/gcc/5','/usr/local/lib'],
            #extra_compile_args=['-fopenmp'],
            extra_compile_args=['-Wno-unused-function', '-Wno-#warnings'],
            #extra_link_args=['-fopenmp']
            #libraries = args.lib,
            #language = 'c++' if args.cplus else 'c',
        ),
    ]

setup(
        name = 'phil-output-extractor',
        version = '0.0.1',
        description = 'tools for producing aggregated hdf5 output from set of FRED realizations',
        author = 'Jay DePasse',
        author_email='depasse@psc.edu',
        ext_modules = cythonize(extensions, force=True),
        packages = ['phil_output_extractor',],
        package_dir = {'': 'src'},
        include_package_data = True,
        scripts = ['src/phil_output_extractor/poe.py',]
        )
