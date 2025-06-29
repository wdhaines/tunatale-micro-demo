from setuptools import setup, find_packages

setup(
    name="tunatale",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask>=2.0.0',
        'python-dotenv>=0.19.0',
        'nltk>=3.6.0',
        'spacy>=3.0.0',
    ],
    package_data={
        '': ['templates/*.html', 'static/*', 'instance/*'],
    },
    include_package_data=True,
    python_requires='>=3.8',
)
