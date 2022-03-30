import sys, os
mod_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if mod_path not in sys.path:
    sys.path.insert(0, mod_path)
from internet_of_fish.modules import (
    collector,
    definitions,
    detector,
    metadata,
    mptools,
    notifier,
    runner,
    uploader,
    utils)
