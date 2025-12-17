'''
JsonTalkie - Json Talkie is intended for direct IoT communication.
Original Copyright (c) 2025 Rui Seixas Monteiro. All right reserved.
This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.
This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.
https://github.com/ruiseixasm/JsonTalkie
'''
from typing import Dict, Any
import time
import random

from broadcast_socket_udp import *
from broadcast_socket_dummy import *
from broadcast_socket_serial import *
from json_talkie import *


class Talker:
    def __init__(self):
        # Defines 'talk', 'list', 'run', 'set', 'get' parameters
        self.manifesto: Dict[str, Dict[str, Any]] = {
            'talker': {
                'name': 'Main',
                'description': 'This device is similar to Buzzer!'
            },
            'run': {
                'buzz': {
                    'description': 'Triggers a 500ms buzzing sound',
                    'function': self.buzz
                },
                'print':{
                    'description': 'Prints the duration on the device',
                    'function': self.print_duration
                }
            },
            'set': {
                'duration': {
                    'description': 'Sets the duration of Buzzing in seconds',
                    'function': self.set_duration
                }
            },
            'get': {
                'duration': {
                    'description': 'Gets the duration of Buzzing in seconds',
                    'function': self.get_duration
                }
            },
            'echo': self.echo,
            'error': self.error
        }
        # Talker self variables
        self._duration: float = 0.5

    def buzz(self, message: Dict[str, Any]) -> bool:
        print(f"\tBUZZING for {self._duration} seconds!\a")
        time.sleep(self._duration) # Take its time
        return True

    def print_duration(self, message: Dict[str, Any]) -> bool:
        print(f"\t{self._duration}")
        return True

    def set_duration(self, message: Dict[str, Any], duration: int) -> bool:
        try:
            self._duration = float(duration)
            return True
        except (ValueError, TypeError):
            # Handle cases where conversion fails
            return False

    def get_duration(self, message: Dict[str, Any]) -> int:
        return self._duration
    

    # Echo codes (g):
    #     0 - ROGER
    #     1 - UNKNOWN
    #     2 - NONE

    def echo(self, message: Dict[str, Any]) -> bool:
        if JsonKey.FROM.value in message:
            print(f"\t[{message[ JsonKey.FROM.value ]}", end='')
            if "w" in message:
                what: str = "echo"
                if isinstance(message["w"], int) and message["w"] >= 0 and message["w"] <= 6:
                    match message["w"]:
                        case 0:
                            what = "talk"
                        case 1:
                            what = "list"
                        case 2:
                            what = "run"
                        case 3:
                            what = "set"
                        case 4:
                            what = "get"
                        case 5:
                            what = "sys"
                    if "g" in message:
                        roger: str = "FAIL"
                        match message[ JsonKey.ROGER.value ]:
                            case 0:
                                roger = "ROGER"
                            case 1:
                                roger = "UNKNOWN"
                            case 2:
                                roger = "NONE"
                        if "n" in message:
                            print(f" {what} {message[ JsonKey.NAME.value ]}]\t{roger}")
                        else:
                            print(f" {what}]\t{roger}")
                    elif "v" in message and "n" in message:
                        print(f" {what} {message[ JsonKey.NAME.value ]}]\t{message[ JsonKey.VALUE.value ]}")
                    elif "n" in message and "d" in message:
                        print(f" {what} {message[ JsonKey.NAME.value ]}]\t{message[ JsonKey.DESCRIPTION.value ]}")
                    elif "n" in message and "r" in message:
                        print(f" {what} {message[ JsonKey.NAME.value ]}]\t{message[ JsonKey.REPLY.value ]}")
                    elif "r" in message:
                        print(f" {what}]\t{message[ JsonKey.REPLY.value ]}")
            elif "d" in message:
                print(f"]\t{message[ JsonKey.DESCRIPTION.value ]}")
        return True


    # Error types (e):
    #     0 - Unknown sender
    #     1 - Message missing the checksum
    #     2 - Message corrupted
    #     3 - Wrong message code
    #     4 - Message NOT identified
    #     5 - Set command arrived too late

    def error(self, message: Dict[str, Any]) -> bool:
        if JsonKey.FROM.value in message:
            print(f"\t[{message[ JsonKey.FROM.value ]}", end='')
            if JsonKey.ERROR.value in message:
                if isinstance(message[ JsonKey.ERROR.value ], int):
                    print(f"]\tERROR", end='')
                    match message[ JsonKey.ERROR.value ]:
                        case 0:
                            print(f"\tUnknown sender")
                        case 1:
                            print(f"\tMessage missing the checksum")
                        case 2:
                            print(f"\tMessage corrupted")
                        case 3:
                            print(f"\tWrong message code")
                        case 4:
                            print(f"\tMessage NOT identified")
                        case 5:
                            print(f"\tMessage echo id mismatch")
                        case 5:
                            print(f"\tSet command arrived too late")
                        case _:
                            print("\tUnknown")
            else:
                print("]\tUnknown error")
        return True


if __name__ == "__main__":

    talker = Talker()
    broadcast_socket: BroadcastSocket = BroadcastSocket_UDP()
    json_talkie: JsonTalkie = JsonTalkie(broadcast_socket, talker.manifesto)

    # Start listening (opens socket)
    if not json_talkie.on():
        print("\tFailed to turn jsonTalkie On!")
        exit(1)
    
    print(f"\tTalker {talker.manifesto['talker']['name']} running. Press Ctrl+C to stop.")
    
    try:
        messages: tuple[Dict[str, Any]] = (
            {JsonKey.MESSAGE.value: 1, JsonKey.TO.value: '*'},
            {JsonKey.MESSAGE.value: 2, "n": 'buzz', JsonKey.TO.value: 'Buzzer'},
            {JsonKey.MESSAGE.value: 2, "n": 'on', JsonKey.TO.value: 'Buzzer'},
            {JsonKey.MESSAGE.value: 2, "n": 'off', JsonKey.TO.value: 'Buzzer'}
        )

        # Main loop
        message_time = time.time()
        while True:
            if time.time() - message_time > 30:
                json_talkie.talk(messages[random.randint(0, len(messages) - 1)])
                message_time = time.time()
    except KeyboardInterrupt:
        print("\tShutting down...")
    finally:
        json_talkie.off()  # Ensures socket cleanup


