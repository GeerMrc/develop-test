from setuptools import setup, find_packages

setup(
    name="tmall-bot",
    version="0.1",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'requests',
        'aiohttp',
        'pyyaml',
        'playwright',
        'pillow'
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-asyncio',
            'pytest-playwright'
        ]
    }
) 