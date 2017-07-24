# distutils: language=c++
# coding:UTF-8

from distutils.core import setup
from Cython.Build import cythonize

setup(ext_modules = cythonize(
           "ged.pyx",
           sources=[],
           language="c++",
      ))

setup(ext_modules = cythonize(
           "lcs.pyx",
           sources=[],
           language="c++",
      ))



