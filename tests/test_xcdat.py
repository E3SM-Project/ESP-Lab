import subprocess
try:
    import xcdat
    print("xcdat is installed")
except ImportError:
    print("xcdat is missing")
