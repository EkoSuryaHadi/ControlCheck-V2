import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps' / 'api'))
# Keep automated test suites hermetic and offline
os.environ['SUMOPOD_API_KEY'] = ''

