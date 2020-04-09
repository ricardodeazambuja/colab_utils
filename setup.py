from setuptools import setup, find_packages
setup(
    name="Colab_Utils",
    version="0.1",
    packages=['colab_utils'],
    install_requires=['ffmpeg-python', 'scipy', 'PIL', 'numpy'],

    # metadata to display on PyPI
    author="Ricardo de Azambuja",
    author_email="ricardo.azambuja@gmail.com",
    description="Some useful (or not so much) Python stuff for Google Colab notebooks",
    keywords="Notebook colab colaboratory google Numpy PIL",
    url="https://github.com/ricardodeazambuja/colab_utils",
    classifiers=[
        'Programming Language :: Python :: 3 :: Only' # https://pypi.org/classifiers/
    ]
)

# https://setuptools.readthedocs.io/en/latest/setuptools.html