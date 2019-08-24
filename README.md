# BinMSGUI
BinMSGUI is a Python Graphical User Interface (GUI) that I developed in order to test MountainSort's (MS) spike sorting algorithm. We use Axona's DacqUSB in order to record in-vivo electrophysiology data in Alzheimer's mice models. That being said, the DacqUSB allows you to record in two modes: Bin (continuous) and Tint (snippets). This package focuses on sorting the continuous Bin data, as MountainSort's curation step requires random sampling of the data to determine if each identified cell exceeds a provided noise overlap parameter. The data is ultimately converted to the Tint format, as we use the Tint software to manually sort and analyze the data. **Note: MountainSort can sort snippets, but it's difficult to curate these results as the algorithm requires random sampling (of non spike data) to determine the noise contamination percentage of each cell.**

# Requirements
- Python: this code was written using Python 3.7, however the compatibility really only depends on PyQt5, which requires Python 2.6+. This was written in Python 3 so I suggest getting the latest version of Python5. It will make the installation process easier as PyQt5 used to be a pain to download in the older versions (3.4 for example). If you happen to have problems downloading PyQ5t, you will need to search for a wheel (.whl) file for PyQt5 for your version (of Python and OS).
- Operating System: BinMSGUI in its current state requires that you have Windows 10, as it will require us downloading the Windows Subsystem for Linux (WSL). If you are a Linux user, it should not be too difficult to add some code that will make BinMSGUI operable with your operating system. Right now I simply am running the terminal commands through WSL via Python. We could likely determine if the user is running on Linux and then just pipe the commands using the os module.
- Windows Subsystem for Linux (WSL): as mentioned in Step 2, we will be using the WSL, therefore you must have that installed. I describe how to install the WSL [here](https://www.geba.technology/project/mountainsort-with-windows-installing-windows-subsystem-for-linux-wsl).
- Bin Formatted Data: this GUI is designed to convert .bin data to the .mda format that MountainSort requires, sort that data using the MountainSort algorithm, and then convert this sorted data to the Tint format. Therefore, the first step is that you must have your data in the .bin file format (recorded from Axona's dacqUSB).
- MountainSort Installed: As I mentioned in step 4, the data will be sorted using MountainSort, therefore you must have MountainSort installed. I have detailed steps on installing MountainSort for the WSL [here](https://www.geba.technology/project/mountainsort-with-windows-installation), however your best bet is to check the [README](https://github.com/flatironinstitute/mountainsort_examples/blob/master/README.md) file from the Flatiron Institute.

# Python Dependencies
- PyQt5
- PyQt5-sip
- NumPy
- SciPy
- matplotlib
- Jupyter

# Documentation
[![gebaSpike: Tutorial](https://geba.s3.amazonaws.com/media/projects/binmsgui-sorting-axona-data-with-mountainsort/BinMSGUI.jpg)](https://geba.technology/project/binmsgui-sorting-axona-data-with-mountainsort)

- [Installation](https://geba.technology/project/binmsgui-sorting-axona-data-with-mountainsort)
- [User Guide](https://geba.technology/project/binmsgui-sorting-axona-data-with-mountainsort-binmsgui-user-guide)

# Authors
* **Geoff Barrett** - [Geoff’s GitHub](https://github.com/GeoffBarrett)

# License
This project is licensed under the GNU  General  Public  License - see the [LICENSE.md](../master/LICENSE) file for details
