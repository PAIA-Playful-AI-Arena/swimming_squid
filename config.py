import sys
from os import path
sys.path.append(path.dirname(__file__))

from src.game import SwimmingSquidSingle

GAME_SETUP = {
    "game": SwimmingSquidSingle,
    # "dynamic_ml_clients":True
}
