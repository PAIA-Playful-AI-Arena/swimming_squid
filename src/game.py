import copy
import os.path

import pandas as pd
import pygame

from mlgame.argument.model import AINameEnum, GroupAI, GroupEnum
from mlgame.game.paia_game import PaiaGame, GameResultState, GameStatus
from mlgame.utils.enum import get_ai_name
from mlgame.utils.logger import logger
from mlgame.view.audio_model import create_sound_init_data, create_music_init_data
from mlgame.view.decorator import check_game_progress, check_game_result, check_scene_init_data
from mlgame.view.view_model import *
from .foods import *
from .game_object import Squid, LevelParams, ScoreText, WindowConfig, ForegroundText
from .game_state import EndingState, OpeningState, RunningState

FOOD_LIST = [Food1, Food2, Food3, Garbage1, Garbage2, Garbage3]
EXTRA_FRAME = 300
EXTRA_POINT = 50


class SwimmingSquid(PaiaGame):
    """
    This is a Interface of a game
    """

    def __init__(
            self,
            level: int = -1,
            level_file: str = "",
            group_ai_list=None,
            *args, **kwargs):
        super().__init__(user_num=1,group_ai_list=group_ai_list)
        if group_ai_list is None:
            ai_path = os.path.join(os.path.dirname(__file__),"..", "ml")
            group_ai_list = [
                GroupAI(group=GroupEnum.O, ai_name=AINameEnum.P1, ai_path=os.path.join(ai_path,"ml_play_manual_1P.py"))
            ]
        self._new_food_frame = 0
        self._music = []
        self._status = GameStatus.GAME_ALIVE
        self._running_state = RunningState.OPENING
        self.game_result_state = GameResultState.FAIL
        self.scene = Scene(width=WIDTH, height=HEIGHT, color=BG_COLOR, bias_x=0, bias_y=0)
        self._level = level
        self._level_file = level_file
        self._used_file = ""
        self.foods = pygame.sprite.Group()
        self.squids = pygame.sprite.Group()
        self._help_texts = pygame.sprite.Group()
        self._fore_help_texts = pygame.sprite.Group()
        self._sounds = []
        # self.sound_controller = SoundController(sound)
        self._overtime_count = 0
        # self._game_times = game_times
        self._winner = []
        self._foods_num = []
        self._foods_max_num = []
        self._game_params = {}
        self._current_round_num = 1
        self._record1 = {
            "player_num": get_ai_name(0),
        }
        self._last_collision = -30
        self._init_game()
        self._state_map = {
            RunningState.OPENING: OpeningState(self),
            RunningState.ENDING: EndingState(self),
        }
        self.current_state = self._state_map[RunningState.OPENING]
        self.ai_enabled=False
        self.group_ai_dict = {ai.ai_name:ai for ai in group_ai_list}
        self.used_frame = 0
        
    def set_game_state(self, state: RunningState):
        
        self._running_state = state
        if state in self._state_map.keys():
            self.current_state = self._state_map[state]
        else:
            self.current_state = None
        if state == RunningState.PLAYING:
            self._init_game()
        if state == RunningState.ENDING:
            self.used_frame = self.frame_count
            self.frame_count = self._frame_limit
            self._frame_limit += 90

    def _init_game_by_file(self, level_file_path: str):
        try:
            with open(level_file_path) as f:
                game_params = LevelParams(**json.load(f))
                self._used_file = level_file_path

        except:
            # If the file doesn't exist, use default parameters
            print("此關卡檔案不存在，遊戲將會會自動使用第一關檔案 001.json。")
            print("This level file is not existed , game will load 001.json automatically.")
            with open(os.path.join(LEVEL_PATH, "001.json")) as f:
                game_params = LevelParams(**json.load(f))
                self._level = 1
                self._level_file = ""
                self._used_file = "001.json"
        finally:
            # set game params
            self._foods_num = [game_params.food_1, game_params.food_2, game_params.food_3, game_params.garbage_1,
                               game_params.garbage_2, game_params.garbage_3]
            self._foods_max_num = [game_params.food_1_max, game_params.food_2_max, game_params.food_3_max,
                                   game_params.garbage_1_max,
                                   game_params.garbage_2_max, game_params.garbage_3_max]

            self.playground = pygame.Rect(
                0, 0,
                game_params.playground_size_w,
                game_params.playground_size_h
            )

            self._score_to_pass = game_params.score_to_pass
            self._frame_limit = game_params.time_to_play

            self.playground.center = (WIDTH / 2, (HEIGHT)/2+60)
            self._food_window = WindowConfig(
                left=self.playground.left, right=self.playground.right,
                top=self.playground.top, bottom=self.playground.bottom)
            self._garbage_window = WindowConfig(
                left=self.playground.left, right=self.playground.right,
                top=self.playground.top - 60, bottom=self.playground.top - 10)

            self._food_pos_list = []
            self._garbage_pos_list = []

            # init game
            self.squid1 = Squid(1, WIDTH/2-game_params.playground_size_w/4, (HEIGHT)/2+20)
            self.squids.empty()
            self.squids.add(self.squid1)
            self.foods.empty()
            for i in range(6):
                self._create_foods(FOOD_LIST[i], self._foods_num[i])

            self.frame_count = 0
            self._last_collision = -30
            self._frame_count_down = self._frame_limit
            self._new_food_frame = 0
            self._overtime_count = 0
            

            self._status = GameStatus.GAME_ALIVE
            game_params.left = self.playground.left
            game_params.right = self.playground.right
            game_params.bottom = self.playground.bottom
            game_params.top = self.playground.top
            self._game_params = game_params


    
    def update(self, commands):
        # handle command
        if isinstance(self.current_state,(OpeningState,EndingState)):
            self.current_state.update()
            self.frame_count += 1

        elif self._running_state == RunningState.RESET:
            return "RESET"
        elif self._running_state == RunningState.PLAYING:
            self.ai_enabled = True
        
            ai_1p_cmd = commands[get_ai_name(0)]
            if ai_1p_cmd is not None:
                action_1 = ai_1p_cmd[0]
            else:
                action_1 = "NONE"

            self.squid1.update(self.frame_count, action_1)
            revise_squid_coordinate(self.squid1, self.playground)
            # create new food
            if self.frame_count - self._new_food_frame > 150:
                for i in range(6):
                    if self._foods_max_num[i] > self._foods_num[i]:
                        self._foods_num[i] += 1
                        self._create_foods(FOOD_LIST[i], 1)
                self._new_food_frame = self.frame_count

            # update sprite
            self.foods.update(playground=self.playground)
            self._help_texts.update()
            self._fore_help_texts.update()
            # handle collision

            self._check_foods_collision()
            # self._timer = round(time.time() - self._begin_time, 3)
            # self._check_squids_collision()

            self.frame_count += 1
            self._frame_count_down = self._frame_limit - self.frame_count
            # self.draw()

            if self.is_passed or self.time_out:
                # 五戰三勝的情況下不能直接回傳，因此紀錄 winner 後，重啟遊戲
                self.update_winner()

                # if self.is_passed:
                #     self._sounds.append(PASS_OBJ)
                # else:
                #     self._sounds.append(FAIL_OBJ)

                status = GameStatus.GAME_ALIVE

                self._status = status

                if self.squid1.score >= self._score_to_pass:  # pass
                    self._status = "GAME_PASS"
                    print("通關！")
                    logger.info("通關！")
                else:
                    self._status = "GAME_OVER"
                    print("時間到！")
                    logger.info("時間到！")
                self.set_game_state(RunningState.ENDING)

                return "RESET"
            else:
                self._status = GameStatus.GAME_ALIVE

        self.ai_enabled = bool(self._running_state == RunningState.PLAYING)

    def _check_foods_collision(self):
        hits = pygame.sprite.groupcollide(self.squids, self.foods, dokilla=False, dokillb=False)
        to_remove_foods = set()

        for squid, foods in hits.items():
            for food in foods:
                if squid.is_paralysis:
                    continue
                squid.eat_food_and_change_level_and_play_sound(food, self._sounds)
                to_remove_foods.add(food)
                if isinstance(food, (Food1, Food2, Food3,)):
                    ScoreText(
                        text=f"+{food.score}",
                        color=SCORE_COLOR_PLUS,
                        x=food.rect.centerx,
                        y=food.rect.centery,
                        groups=self._help_texts
                    )
                    self._sounds.append(EATING_GOOD_OBJ)
                elif isinstance(food, (Garbage1, Garbage2, Garbage3,)):
                    ScoreText(
                        text=f"{food.score}",
                        color=SCORE_COLOR_MINUS,
                        x=food.rect.centerx,
                        y=food.rect.centery,
                        groups=self._help_texts
                    )
                    self._sounds.append(EATING_BAD_OBJ)
        for food in to_remove_foods:
            food.kill()
            self._create_foods(food.__class__, 1)

    def get_data_from_game_to_player(self):
        """
        send something to game AI
        we could send different data to different ai
        """
        to_players_data = {}

        foods_data = [
            {
                "x": food.rect.centerx,
                "y": food.rect.centery,
                "w": food.rect.width,
                "h": food.rect.height,
                "type": str(food.type),
                "score": food.score
            }
            for food in self.foods
            if (
                    food.rect.bottom > self.playground.top and
                    food.rect.top < self.playground.bottom and
                    food.rect.right > self.playground.left and
                    food.rect.left < self.playground.right
            )
        ]
        data_to_1p = {
            "frame": self.frame_count,
            "self_x": self.squid1.rect.centerx,
            "self_y": self.squid1.rect.centery,
            "self_w": self.squid1.rect.width,
            "self_h": self.squid1.rect.height,
            "self_vel": self.squid1.vel,
            "self_lv": self.squid1.lv,
            "opponent_x": self.playground.center[0],
            "opponent_y": self.playground.center[1]-40,
            "opponent_lv": 1,
            "opponent_w": 30,
            "opponent_h": 60,
            "opponent_vel": 30,
            "foods": foods_data,
            "score": self.squid1.score,
            "score_to_pass": self._score_to_pass,
            "status": self.get_game_status(),
            "env": self._game_params.__dict__
        }

        to_players_data[get_ai_name(0)] = data_to_1p
        # should be equal to config. GAME_SETUP["ml_clients"][0]["name"]

        return to_players_data

    def get_game_status(self):

        return self._status

    def reset(self):
        # 重新啟動遊戲
        self.set_game_state(RunningState.OPENING)
        self._current_round_num = 1
        self._winner.clear()
        self._record1 = {
            "player_num": get_ai_name(0),
        }
        self._init_game()

    def _init_game(self):
        if path.isfile(self._level_file):
            # set by injected file
            self._init_game_by_file(self._level_file)
        else:
            level_file_path = os.path.join(LEVEL_PATH, f"{self._level:03d}.json")
            self._level_file = level_file_path
            self._init_game_by_file(level_file_path)

    @property
    def is_passed(self):
        if self.squid1.score >= self._score_to_pass:  # 達成目標分數
            return True
        else:
            return False

    @property
    def time_out(self):
        if self.frame_count >= self._frame_limit:
            # logger.info("時間到")
            return True
        else:
            return False

    @property
    def is_running(self):
        return (not self.time_out)
        # return (not self.time_out) and (not self.is_passed)


    @check_scene_init_data
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
                create_asset_init_data("bg", 1280, 768, BG_PATH, BG_URL),
                create_asset_init_data(SQUID1_HURT_1_ID, SQUID_W, SQUID_H, SQUID1_HURT_1_PATH, SQUID1_HURT_1_URL),
                create_asset_init_data(SQUID1_HURT_2_ID, SQUID_W, SQUID_H, SQUID1_HURT_2_PATH, SQUID1_HURT_2_URL),
                create_asset_init_data(SQUID1_1_ID, SQUID_W, SQUID_H, SQUID1_1_PATH, SQUID1_1_URL),
                create_asset_init_data(SQUID1_2_ID, SQUID_W, SQUID_H, SQUID1_2_PATH, SQUID1_2_URL),
                create_asset_init_data(SQUID1_3_ID, SQUID_W, SQUID_H, SQUID1_3_PATH, SQUID1_3_URL),
                create_asset_init_data(SQUID1_4_ID, SQUID_W, SQUID_H, SQUID1_4_PATH, SQUID1_4_URL),
                create_asset_init_data(SQUID1_5_ID, SQUID_W, SQUID_H, SQUID1_5_PATH, SQUID1_5_URL),
                create_asset_init_data(SQUID1_LOVELY_ID, SQUID_W, SQUID_H, SQUID1_LOVELY_PATH, SQUID1_LOVELY_URL),

                
                create_asset_init_data("scorebar", 1000, 150, SCOREBAR_PATH, SCOREBAR_URL),
                # create_asset_init_data("star", SQUID_H, SQUID_H, STAR_PATH, STAR_URL),
                create_asset_init_data(IMG_ID_FOOD01_L, FOOD_LV1_SIZE, FOOD_LV1_SIZE, FOOD01_L_PATH, FOOD01_L_URL),
                create_asset_init_data(IMG_ID_FOOD02_L, FOOD_LV2_SIZE, FOOD_LV2_SIZE, FOOD02_L_PATH, FOOD02_L_URL),
                create_asset_init_data(IMG_ID_FOOD03_L, FOOD_LV3_SIZE, FOOD_LV3_SIZE, FOOD03_L_PATH, FOOD03_L_URL),
                create_asset_init_data(IMG_ID_FOOD01_R, FOOD_LV1_SIZE, FOOD_LV1_SIZE, FOOD01_R_PATH, FOOD01_R_URL),
                create_asset_init_data(IMG_ID_FOOD02_R, FOOD_LV2_SIZE, FOOD_LV2_SIZE, FOOD02_R_PATH, FOOD02_R_URL),
                create_asset_init_data(IMG_ID_FOOD03_R, FOOD_LV3_SIZE, FOOD_LV3_SIZE, FOOD03_R_PATH, FOOD03_R_URL),
                create_asset_init_data("garbage01", FOOD_LV1_SIZE, FOOD_LV1_SIZE, GARBAGE01_PATH, GARBAGE01_URL),
                create_asset_init_data("garbage02", FOOD_LV2_SIZE, FOOD_LV2_SIZE, GARBAGE02_PATH, GARBAGE02_URL),
                create_asset_init_data("garbage03", FOOD_LV3_SIZE, FOOD_LV3_SIZE, GARBAGE03_PATH, GARBAGE03_URL),
                create_asset_init_data(IMG_ID_OPENNING_BG, 1280, 768, OPENNING_BG_PATH, OPENNING_BG_URL),
                create_asset_init_data(IMG_ID_OPENNING_LOGO, 506, 256, OPENNING_LOGO_PATH, OPENNING_LOGO_URL),
                create_asset_init_data(IMG_ID_TRANSITION_BG, 1280, 768, TRANSITION_BG_PATH, TRANSITION_BG_URL),
                create_asset_init_data(IMG_ID_CLEAR, 1280, 768, CLEAR_PATH, CLEAR_URL),
                create_asset_init_data(IMG_ID_FAILED, 1280, 768, FAILED_PATH, FAILED_URL),
            ],
            "background": [
                # create_image_view_data(
                #     'bg', self.playground.x, self.playground.y,
                #     self.playground.w, self.playground.h)
            ],
            "musics": [
                create_music_init_data("bgm01", file_path=BGM01_PATH, github_raw_url=BGM01_URL),
                create_music_init_data("bgm02", file_path=BGM02_PATH, github_raw_url=BGM02_URL),
                create_music_init_data("bgm03", file_path=BGM03_PATH, github_raw_url=BGM03_URL),

            ],
            # Create the sounds list using create_sound_init_data
            "sounds": [
                create_sound_init_data("eat_good_food", file_path=EATING_GOOD_PATH, github_raw_url=EATING_GOOD_URL),
                create_sound_init_data("eat_bad_food", file_path=EATING_BAD_PATH, github_raw_url=EATING_BAD_URL),
                create_sound_init_data("pass", file_path=PASS_PATH, github_raw_url=PASS_URL),
                create_sound_init_data("lv_up", file_path=LV_UP_PATH, github_raw_url=LV_UP_URL),
                create_sound_init_data("lv_down", file_path=LV_DOWN_PATH, github_raw_url=LV_DOWN_URL),
                create_sound_init_data("collision", file_path=COLLISION_PATH, github_raw_url=COLLISION_URL)
            ]
        }
        return scene_init_data

    @property
    def _p1_info(self):
        scorebar1_width = 740-remap(self.squid1.score, 0, self._score_to_pass, 10, 740)
        result = [
            create_rect_view_data("squid1_scorebar",WIDTH-380-scorebar1_width, 45, scorebar1_width, 55, "#000000CC"),
        ]
        dot_y = 100

        result.extend(
            [
                # create_text_view_data(f"{self.group_ai_dict[AINameEnum.P1.value].ai_label}", (WIDTH/2-570), 10, "#EEEEEE", "20px Krungthep BOLD"),
                create_text_view_data(f"Lv{self.squid1.lv}", WIDTH/2-500, dot_y, "#EEEEEE", "20px Krungthep BOLD"),
                create_text_view_data(f"{self.squid1.score:03d} / {self._score_to_pass:03d}", (WIDTH/2-500)+30, 65, "#EEEEEE", "24px Krungthep BOLD"),

            ]
        )
        return result

    @check_game_progress
    def get_scene_progress_data(self):
        """
        Get the position of game objects for drawing on the web
        """
        if isinstance(self.current_state,(OpeningState,EndingState)):
            return self.current_state.get_scene_progress_data()
        elif self._running_state != RunningState.PLAYING:
            return create_scene_progress_data(frame=self.frame_count)
        
        foods_data = [food.game_object_data for food in self.foods]

        game_obj_list = [self.squid1.game_object_data]
        help_texts = [
            obj.game_object_data for obj in self._help_texts
        ]
        game_obj_list.extend(foods_data)
        game_obj_list.extend(help_texts)
        toggle_objs = [
            create_text_view_data(f"{self._level_file.split('/')[-1]}", 10, HEIGHT-20, "#EEEEEE", "14px Krungthep"),
        ]

        game_obj_list.extend(foods_data)
        backgrounds = [
            create_image_view_data('bg', 0, 0,WIDTH,HEIGHT),
            create_rect_view_data('mask1', 0, 0,WIDTH,self.playground.y,"#00000088"),
            create_rect_view_data('mask2', 0, self.playground.y+self.playground.h,  WIDTH,max(HEIGHT-self.playground.bottom,0),"#00000088"),
            create_rect_view_data('mask3', 0, self.playground.top, self.playground.left,self.playground.height,"#00000088"),
            create_rect_view_data('mask4', self.playground.right, self.playground.top,max(WIDTH-self.playground.right,0),self.playground.height,"#00000088"),

        ]
        foregrounds = [
            create_image_view_data("scorebar", (WIDTH-1000)/2, 0, 1000, 150),

            create_text_view_data(f"{self._frame_count_down:04d}", WIDTH*2/3+84, 38, "#EEEEEE", "48px Krungthep BOLD"),
            
        ]
        foregrounds.extend(self._p1_info)
        foregrounds.extend([obj.game_object_data for obj in self._fore_help_texts])
        scene_progress = create_scene_progress_data(
            frame=self.frame_count, background=backgrounds,
            object_list=game_obj_list,
            foreground=foregrounds,
            toggle=toggle_objs,
            musics=self._music,
            sounds=self._sounds
        )
        self._sounds = []

        # self._music = []
        return scene_progress

    @check_game_result
    def get_game_result(self):
        """
        send game result
        """
        self.game_result_state = GameResultState.FINISH
        #  update record data
        self._record1['squid'] = '1P'
        self._record1['rank'] = self.squid1.rank
        self._record1['score'] = self.squid1.score
        self._record1['passed'] = self.is_passed

        return {
            "frame_used": self.frame_count,
            "status": self.game_result_state,
            "attachment": [
                self._record1
            ]
        }

    def get_keyboard_command(self):
        """
        Define how your game will run by your keyboard
        """
        cmd_1p = []
        cmd_2p = []
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
            if isinstance(food, (Food1, Food2, Food3,)):
                # if food pos list is empty , re-create
                self._set_food_position(food)


            elif isinstance(food, (Garbage1, Garbage2, Garbage3,)):
                if len(self._garbage_pos_list) < 1:
                    self._garbage_pos_list = divide_window_into_grid(self._garbage_window, rows=3, cols=10)
                pos = self._garbage_pos_list.pop()
                food.set_center_x_and_y(
                    pos[0],
                    pos[1]
                )
        pass

    def _set_food_position(self, food):
        # 設定食物的位置
        while True:
            if len(self._food_pos_list) < 1:
                # 如果食物位置列表為空，則重新生成食物位置列表，確保食物生成的位置是平均的
                self._food_pos_list = divide_window_into_grid(self._food_window)
            pos = self._food_pos_list.pop()
            food.set_center_x_and_y(pos[0], pos[1])
            if not self._is_food_collided_with_squids(food):
                break

            
    def _is_food_collided_with_squids(self, food):
        """
        Detects if a food item will collide with both squids.
        """
        squid1_collision = pygame.sprite.collide_rect_ratio(2.0)( food, self.squid1)
        return squid1_collision
        

    def update_winner(self):
        self._record1[f"round{self._current_round_num}"] = self.squid1.score
        temp_records = [self._record1]
        print(pd.DataFrame(temp_records).to_string())


def revise_squid_coordinate(squid: Squid, playground: pygame.Rect):
    squid_rect = copy.deepcopy(squid.rect)
    if squid_rect.left < playground.left:
        squid_rect.left = playground.left
    elif squid_rect.right > playground.right:
        squid_rect.right = playground.right

    if squid_rect.top < playground.top:
        squid_rect.top = playground.top
    elif squid_rect.bottom > playground.bottom:
        squid_rect.bottom = playground.bottom
    squid.rect = squid_rect
    pass


def divide_window_into_grid(window: WindowConfig, rows: int = 6, cols: int = 8) -> list[(int, int)]:
    grid_positions = []

    # Calculate width and height of each grid piece
    width = (window.right - window.left) // cols
    height = (window.bottom - window.top) // rows

    # Generate grid positions
    for row in range(rows):
        for col in range(cols):
            center_x = window.left + col * width + width // 2
            center_y = window.top + row * height + height // 2
            grid_positions.append((center_x, center_y))

    # Shuffle the list to randomize the order of positions
    random.shuffle(grid_positions)

    return grid_positions


def remap(value: int, fromLow: int, fromHigh: int, toLow: int, toHigh: int):

    if fromLow > fromHigh:
        raise ValueError("fromLow must be less than fromHigh")
    if toLow > toHigh:
        raise ValueError("toLow must be less than toHigh")
    if value < fromLow:
        return toLow
    elif value > fromHigh:
        return toHigh
    return (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow


