from setuptools import setup, find_packages

setup(
    name="tunatale",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'nltk>=3.6.0',
        'spacy>=3.0.0',
    ],
    package_data={
        '': ['static/*', 'instance/*'],
    },
    include_package_data=True,
    python_requires='>=3.8',
)
