from setuptools import setup, find_packages

setup(
    name='mkdocs-list-callouts-plugin',
    version='0.1.0',
    author='EmergentTwilight',
    description='MkDocs List Callouts Plugin',
    url='https://github.com/EmergentTwilight/mkdocs-list-callouts-plugin',
    python_requires='>=3.8',
    install_requires=[
        'mkdocs>=1.4.0',
    ],
    entry_points={
        'mkdocs.plugins': [
            'list_callouts = list_callouts:ListCalloutsPlugin'
        ]
    },
    include_package_data=False,
)