from setuptools import find_packages, setup

setup(
    name='degree_day',
    packages=find_packages(include=['degree_day']),
    version='0.1.0',
    description='Library of functions to compute and work with degree day phenology models',
    author='Tim Farkas',
    install_requires=['sympy', 'numpy', 'pandas', 'geopandas', 'pyyaml', 'xarray', 'rioxarray'],
)