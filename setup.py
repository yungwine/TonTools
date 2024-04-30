from setuptools import setup, find_packages

requirements = [
    "setuptools>=69.5",
    "tonsdk~=1.0.13",
    "ton~=0.26",
    "aiohttp~=3.9",
    "requests~=2.31",
    "pytonlib~=0.0.46",
    "graphql-query~=1.3",
]

setup(
    name='TonTools',
    version='2.2.0',
    packages=find_packages(),
    include_package_data=True,
    url='',
    license='MIT License',
    author='yungwine',
    author_email='cyrbatoff@gmail.com',
    description='Explore TON Blockchain with python',
    install_requires=requirements,
)
