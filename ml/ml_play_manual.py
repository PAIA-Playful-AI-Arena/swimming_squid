import random
from pprint import pprint

import orjson
import pygame


class MLPlay:
    def __init__(self,ai_name,*args,**kwargs):
        print("Initial ml script")

    def update(self, scene_info: dict, keyboard:list=[], *args, **kwargs):
        """
        Generate the command according to the received scene information
        """
        # pprint("AI received data from game :", orjson.dumps(scene_info))
        pprint(scene_info)
        assert scene_info['env']['left']
        actions = []

        if pygame.K_w in keyboard or pygame.K_UP in keyboard:
            actions.append("UP")
        elif pygame.K_s in keyboard or pygame.K_DOWN in keyboard:
            actions.append("DOWN")

        elif pygame.K_a in keyboard or pygame.K_LEFT in keyboard:
            actions.append("LEFT")
        elif pygame.K_d in keyboard or pygame.K_RIGHT in keyboard:
            actions.append("RIGHT")
        else:
            actions.append("NONE")

        return actions



    def reset(self):
        """
        Reset the status
        """
        print("reset ml script")
        pass
