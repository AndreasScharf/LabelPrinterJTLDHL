import os
import sys

def base_dir():
    """Return the folder where the EXE or script is located."""
    if getattr(sys, 'frozen', False):  # running as EXE
        return os.path.dirname(sys.executable)
    else:  # running from source
        return os.path.dirname(os.path.abspath(__file__))

def asset_path(filename):
    """Return full path to an asset file in the assets folder."""
    return os.path.join(base_dir(), "assets", filename)

