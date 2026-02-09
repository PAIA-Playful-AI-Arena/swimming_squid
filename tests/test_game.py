from http import HTTPStatus

import requests
from loguru import logger

from ..src.game import SwimmingSquidSingle, remap

from ..src.game_state import EndingState, OpeningState, RunningState, TransitionState
def test_set_game_state():
    game = SwimmingSquidSingle()
    game.set_game_state(RunningState.OPENING)
    assert isinstance(game.current_state,OpeningState)
    game.set_game_state(RunningState.TRANSITION)
    assert isinstance(game.current_state,TransitionState)
    game.set_game_state(RunningState.ENDING)
    assert isinstance(game.current_state,EndingState)

def test_set_game_state_invalid():
    game = SwimmingSquidSingle()
    game.set_game_state(RunningState.RESET)
    assert game.current_state is None
    game.set_game_state(RunningState.PLAYING)
    assert game.current_state is None


def test_remap():
    assert remap(100, 0, 100, 0, 1000) == 1000
    assert remap(0, 0, 100, 0, 1000) == 0
    assert remap(50, 0, 50, 0, 1000) == 1000
    assert remap(-10, 0, 50, 0, 1000) == 0


def test_resource_available():
    game = SwimmingSquidSingle()
    scene_info = game.get_scene_init_data()
    asset = scene_info['assets']
    for obj in asset:
        resp = requests.get(obj['url'])
        assert resp.status_code == HTTPStatus.OK , obj['url'] +"\n"+ resp.text
        logger.info(f"get {obj['url']} successfully")