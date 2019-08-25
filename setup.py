import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

pkgs = setuptools.find_packages()
print('found these packages:', pkgs)

pkg_name = "BinMSGUI"

setuptools.setup(
    name=pkg_name,
    version="1.0.3",
    author="Geoffrey Barrett",
    author_email="geoffrey.m.barrett@gmail.com",
    description="BinMSGUI, sorts .bin data through MountainSort and exports as Tint format.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HussainiLab/BinMSGUI.git",
    packages=pkgs,
    install_requires=
    [
        'PyQt5',
        'numpy',
        'scipy',
        'matplotlib',
        'jupyter'
    ],
    package_data={'BinMSGUI': ['img/*.png']},
    classifiers=[
        "Programming Language :: Python :: 3.7 ",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3) ",
        "Operating System :: OS Independent",
    ],
)
