from enum import Enum
from math import sin
from random import randint

from mlgame.view.audio_model import MusicProgressSchema

from .env import HEIGHT, IMG_ID_CLEAR, IMG_ID_FAILED, IMG_ID_OPENNING_BG, IMG_ID_OPENNING_LOGO, IMG_ID_TRANSITION_BG, PASS_OBJ, WIDTH
from mlgame.game.paia_game import GameState
from mlgame.view.view_model import create_image_view_data, create_scene_progress_data, create_text_view_data


class EndingState(GameState):
    def __init__(self,game):
        self._game = game
        self.frame_count = 0
        self._info_text = {}
        self._sound = [PASS_OBJ]
        self._p1_score = 0
        self._pass_score = 0
        self.reset()
    def update(self):
        if self.frame_count == 0:
            self._sound = [PASS_OBJ]
        else:
            self._sound = []

        if 0 < self.frame_count < 120:

            pass
        elif 90 <= self.frame_count:
            self.reset()
            self._game.set_game_state(RunningState.RESET)
            
        self.frame_count += 1
    def get_scene_progress_data(self):
        object_list = []
        self._p1_score = self._game.squid1.score
        self._pass_score = self._game._score_to_pass
        if self._p1_score >= self._pass_score:
            object_list.extend([create_image_view_data(IMG_ID_CLEAR, 0, 0, 1280, 768)])
        else:
            object_list.extend([create_image_view_data(IMG_ID_FAILED, 0, 0, 1280, 768)])
        object_list.extend([create_text_view_data(f"Time : {self._game.frame_count:04d}", WIDTH/2-100, HEIGHT/2, "#EEEEEE", "60px Krungthep"),
                            create_text_view_data(f"Score : {self._p1_score:03d} / {self._pass_score:03d}", WIDTH/2-100, HEIGHT/2+120, "#EEEEEE", "60px Krungthep")])

        
        
        return create_scene_progress_data(
            frame=self.frame_count,
            background=[
                create_image_view_data(IMG_ID_TRANSITION_BG, 0, 0, 1280, 768),
                ],
            object_list=object_list,
            foreground=[],
            toggle=[],
            musics=[], sounds=self._sound
            )
    def reset(self):
        self.frame_count = 0
        self._info_text = create_text_view_data("Ending", 130, 0, "#EEEEEE", "64px Krungthep")
        self._sound = [PASS_OBJ]

class OpeningState(GameState):
    def __init__(self, game: 'SwimmingSquidBattle'):
        self._game = game
        self.frame_count = 0
        # self._ready_text = create_text_view_data("Ready", 300, 300, "#EEEEEE", "64px Consolas BOLD")
        # self._go_text = create_text_view_data("Go! ", -300, -360, "#EEEEEE", "64px Consolas BOLD")
        self._logo_bias_degree = 0
        self._logo_bias = sin(self._logo_bias_degree)
    def update(self):
        if self.frame_count < 90:
            self._logo_bias_degree += 0.15
            self._logo_bias = 15*sin(self._logo_bias_degree)
        elif 90 <= self.frame_count:
            self.frame_count=0
            self.reset()
            self._game.set_game_state(RunningState.PLAYING)
        self.frame_count += 1

    def get_scene_progress_data(self):
        return create_scene_progress_data(
            frame=self.frame_count,
            background=[
                create_image_view_data(IMG_ID_OPENNING_BG, 0, 0, 1280, 768),
                create_image_view_data(IMG_ID_OPENNING_LOGO, 1280/2-506/2, 768/2-256/2+self._logo_bias, 506, 256),
                ],
            object_list=[
                # self._ready_text, self._go_text
                ],
            foreground=[],
            toggle=[],
            musics=[MusicProgressSchema(music_id=f"bgm0{randint(1, 3)}").__dict__] if self.frame_count == 2 else [],
            sounds=[]
            )

    def reset(self):
        self.frame_count = 0
        self._logo_bias_degree = 0
        self._logo_bias = sin(self._logo_bias_degree)

class RunningState(Enum):
    OPENING = 0
    TRANSITION = 1
    ENDING = 2
    PLAYING = 3
    RESET = 4
