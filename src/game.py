import copy
import json
import os.path

import pygame

from mlgame.game.paia_game import PaiaGame, GameResultState, GameStatus
from mlgame.utils.enum import get_ai_name
from mlgame.utils.prof import timeit_in_perf
from mlgame.view.decorator import check_game_progress, check_game_result
from mlgame.view.view_model import *
from .env import *
from .foods import *
from .game_object import Squid, LevelParams
from .sound_controller import SoundController


def revise_ball(ball: Squid, playground: pygame.Rect):
    ball_rect = copy.deepcopy(ball.rect)
    if ball_rect.left < playground.left:
        ball_rect.left = playground.left
    elif ball_rect.right > playground.right:
        ball_rect.right = playground.right

    if ball_rect.top < playground.top:
        ball_rect.top = playground.top
    elif ball_rect.bottom > playground.bottom:
        ball_rect.bottom = playground.bottom
    ball.rect = ball_rect
    pass


class EasyGame(PaiaGame):
    """
    This is a Interface of a game
    """

    def __init__(
            self,
            level: int = -1,
            level_file: str = "",
            sound: str = "off",
            *args, **kwargs):
        super().__init__(user_num=1)
        self.game_result_state = GameResultState.FAIL
        self.scene = Scene(width=WIDTH, height=HEIGHT, color=BG_COLOR, bias_x=0, bias_y=0)
        self._level = level
        self._level_file = level_file
        self.foods = pygame.sprite.Group()
        self.sound_controller = SoundController(sound)

        self._init_game()

    @timeit_in_perf
    def _init_game_by_file(self, level_file_path: str):
        try:
            with open(level_file_path) as f:
                game_params = LevelParams(**json.load(f))

        except:
            # If the file doesn't exist, use default parameters
            print("此關卡檔案不存在，遊戲將會會自動使用第一關檔案 001.json。")
            print("This level file is not existed , game will load 001.json automatically.")
            with open(os.path.join(LEVEL_PATH, "001.json")) as f:
                game_params = json.load(f)
                self._level = 1
                self._level_file = ""
        finally:
            # set game params
            self.playground = pygame.Rect(
                0, 0,
                game_params.playground_size_h,
                game_params.playground_size_w
            )

            self._score_to_pass = game_params.score_to_pass
            self._frame_limit = game_params.time_to_play
            self.playground.center = ((WIDTH-200) / 2, HEIGHT / 2)

            # init game
            self.ball = Squid()
            self.foods.empty()
            self._create_foods(Food1, game_params.food_1)
            self._create_foods(Food2, game_params.food_2)
            self._create_foods(Food3, game_params.food_3)
            self._create_foods(Garbage1, game_params.garbage_1)
            self._create_foods(Garbage2, game_params.garbage_2)
            self._create_foods(Garbage3, game_params.garbage_3)

            self.frame_count = 0
            self._frame_count_down = self._frame_limit
            self.sound_controller.play_music()

    def update(self, commands):
        # handle command
        ai_1p_cmd = commands[get_ai_name(0)]
        if ai_1p_cmd is not None:
            action = ai_1p_cmd[0]
        else:
            action = "NONE"

        self.ball.update(action)
        revise_ball(self.ball, self.playground)
        # update sprite
        self.foods.update(playground=self.playground, squid=self.ball)

        # handle collision

        self._check_foods_collision()
        # self._timer = round(time.time() - self._begin_time, 3)

        self.frame_count += 1
        self._frame_count_down = self._frame_limit - self.frame_count
        # self.draw()

        if not self.is_running:
            return "RESET"

    def _check_foods_collision(self):
        hits = pygame.sprite.spritecollide(self.ball, self.foods, True)
        if hits:
            for food in hits:
                # self.ball.score += food.score
                # growth play special sound
                self.ball.eat_food_and_change_level_and_play_sound(food, self.sound_controller)
                self._create_foods(food.__class__, 1)
                if isinstance(food, (Food1, Food2, Food3,)):
                    self.sound_controller.play_eating_good()
                elif isinstance(food, (Garbage1, Garbage2, Garbage3,)):
                    self.sound_controller.play_eating_bad()

    def get_data_from_game_to_player(self):
        """
        send something to game AI
        we could send different data to different ai
        """
        to_players_data = {}
        foods_data = []
        for food in self.foods:
            # TODO 確認要提供中心點座標還是左上角座標。
            foods_data.append({"x": food.rect.centerx, "y": food.rect.centery, "type": food.type, "score": food.score})

        data_to_1p = {
            "frame": self.frame_count,
            # TODO 確認要提供中心點座標還是左上角座標。
            "player_x": self.ball.rect.centerx,
            "player_y": self.ball.rect.centery,
            "player_size": self.ball.rect.width,
            "player_vel": self.ball.vel,
            "foods": foods_data,

            "score": self.ball.score,
            "score_to_pass": self._score_to_pass,
            "status": self.get_game_status()

        }

        to_players_data[get_ai_name(0)] = data_to_1p
        # should be equal to config. GAME_SETUP["ml_clients"][0]["name"]

        return to_players_data

    def get_game_status(self):

        if self.is_running:
            status = GameStatus.GAME_ALIVE
        elif self.is_passed:
            status = GameStatus.GAME_PASS
        else:
            status = GameStatus.GAME_OVER
        return status

    def reset(self):

        if self.is_passed:
            self._level += 1
            self.sound_controller.play_cheer()
        else:
            self.sound_controller.play_fail()
        self._init_game()

        pass

    def _init_game(self):
        if path.isfile(self._level_file):
            # set by injected file
            self._init_game_by_file(self._level_file)
            pass
        else:
            level_file_path = os.path.join(LEVEL_PATH, f"{self._level:03d}.json")
            self._init_game_by_file(level_file_path)

    @property
    def is_passed(self):
        return self.ball.score > self._score_to_pass

    @property
    def is_running(self):
        return self.frame_count < self._frame_limit

    def get_scene_init_data(self):
        """
        Get the initial scene and object information for drawing on the web
        """
        # bg_path = path.join(ASSET_PATH, "img/background.jpg")
        # background = create_asset_init_data(
        #     "background", WIDTH, HEIGHT, bg_path,
        #     github_raw_url="https://raw.githubusercontent.com/PAIA-Playful-AI-Arena/easy_game/main/asset/img/background.jpg")

        scene_init_data = {
            "scene": self.scene.__dict__,
            "assets": [
                create_asset_init_data("bg", 1000, 1000, BG_PATH, BG_URL),
                create_asset_init_data("squid", SQUID_W, SQUID_H, SQUID_PATH, SQUID_URL),
                create_asset_init_data("food01", FOOD_LV1_SIZE, FOOD_LV1_SIZE, FOOD01_PATH, FOOD01_URL),
                create_asset_init_data("food02", FOOD_LV2_SIZE,FOOD_LV2_SIZE, FOOD02_PATH, FOOD02_URL),
                create_asset_init_data("food03", FOOD_LV3_SIZE,FOOD_LV3_SIZE, FOOD03_PATH, FOOD03_URL),
                create_asset_init_data("garbage01", FOOD_LV1_SIZE,FOOD_LV1_SIZE, GARBAGE01_PATH, GARBAGE01_URL),
                create_asset_init_data("garbage02", FOOD_LV2_SIZE,FOOD_LV2_SIZE, GARBAGE02_PATH, GARBAGE02_URL),
                create_asset_init_data("garbage03", FOOD_LV3_SIZE,FOOD_LV3_SIZE, GARBAGE03_PATH, GARBAGE03_URL),
            ],
            "background": [
                # create_image_view_data(
                #     'bg', self.playground.x, self.playground.y,
                #     self.playground.w, self.playground.h)
            ]
            # "audios": {}
        }
        return scene_init_data

    @check_game_progress
    def get_scene_progress_data(self):
        """
        Get the position of game objects for drawing on the web
        """
        foods_data = []
        for food in self.foods:
            foods_data.append(food.game_object_data)
        game_obj_list = [self.ball.game_object_data]
        game_obj_list.extend(foods_data)
        backgrounds = [
            # create_image_view_data("background", 0, 0, WIDTH, HEIGHT),
            # create_rect_view_data(
            #     "playground", self.playground.x, self.playground.y,
            #     self.playground.w, self.playground.h, PG_COLOR)
            create_image_view_data(
                'bg', self.playground.x, self.playground.y,
                self.playground.w, self.playground.h)
        ]
        foregrounds = [

        ]
        toggle_objs = [
            create_text_view_data(f"Score: {self.ball.score:04d}", 750, 50, "#EEEEEE", "24px Arial BOLD"),
            create_text_view_data(f"Next : {self._score_to_pass:04d}", 750, 100, "#EEEEEE", "24px Arial BOLD"),
            create_text_view_data(f"Time : {self._frame_count_down:04d}", 750, 150, "#EEEEEE", "24px Arial BOLD"),

        ]
        scene_progress = create_scene_progress_data(frame=self.frame_count, background=backgrounds,
                                                    object_list=game_obj_list,
                                                    foreground=foregrounds, toggle=toggle_objs)
        return scene_progress

    @check_game_result
    def get_game_result(self):
        """
        send game result
        """
        if self.get_game_status() == GameStatus.GAME_PASS:
            self.game_result_state = GameResultState.FINISH
        return {"frame_used": self.frame_count,
                "state": self.game_result_state,
                "attachment": [
                    {
                        "player": get_ai_name(0),
                        "rank": 1,
                        "score": self.ball.score,
                        "passed": self.is_passed
                    }
                ]

                }

    def get_keyboard_command(self):
        """
        Define how your game will run by your keyboard
        """
        cmd_1p = []
        key_pressed_list = pygame.key.get_pressed()
        if key_pressed_list[pygame.K_UP]:
            cmd_1p.append("UP")
        elif key_pressed_list[pygame.K_DOWN]:
            cmd_1p.append("DOWN")
        elif key_pressed_list[pygame.K_LEFT]:
            cmd_1p.append("LEFT")
        elif key_pressed_list[pygame.K_RIGHT]:
            cmd_1p.append("RIGHT")
        else:
            cmd_1p.append("NONE")
        return {get_ai_name(0): cmd_1p}

    def _create_foods(self, FOOD_TYPE, count: int = 5):
        for i in range(count):
            # add food to group
            food = FOOD_TYPE(self.foods)
            food.set_center_x_and_y(
                random.randint(self.playground.left, self.playground.right),
                random.randint(self.playground.top, self.playground.bottom)
            )

        pass
