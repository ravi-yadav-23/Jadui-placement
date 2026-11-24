import os
import sys

# Make `app` and `modules` importable when pytest is run from backend/.
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
