# openformat-to-obj
Converts OPENIV (GTA5) odr files to wavefront obj files.

Useful for viewing or modifiying GTA5 3D models.

Requirements
--------------
- OpenIV 2.8
- Python3 (https://www.python.org/downloads/)

Usage
--------------
The script requires 1 argument - a glob or filepath to one or many odr files

By default it checks for a pre-existing obj file, if it finds one that it created previously, it will not run the conversion on that particular odr file.

To overide this behaviour, add the optional argument '-f' or  '--force', and it will re-convert those odr files.

Example
--------------
  python3 openformat-to-obj.py **/*.odr -f
