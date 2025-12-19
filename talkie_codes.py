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
from enum import Enum, IntEnum
from typing import Union, cast, Optional


class TalkieKey(Enum):
    SOURCE      = "c"
    CHECKSUM    = "c"
    TIMESTAMP   = "i"
    IDENTITY    = "i"
    MESSAGE     = "m"
    FROM        = "f"
    TO          = "t"
    INFO        = "s"
    ACTION      = "a"
    ROGER       = "r"


class TalkieCode(IntEnum):
    """Mixin with shared functionality for Talkie codes (enums)"""

    def __str__(self) -> str:
        """String representation is lowercase"""
        return self.name.lower()
    
    @classmethod
    def from_name(cls, name: str) -> Union['Enum', None]:
        """Returns the TalkieCode based on a lower case name"""
        try:
            return cls[name.upper()]    # TalkieCode is in upper case
        except KeyError:
            return None


class SourceValue(TalkieCode):
    REMOTE, LOCAL, SELF, NONE = range(4)


class MessageValue(TalkieCode):
    TALK, CHANNEL, PING, CALL, LIST, INFO, ECHO, ERROR, NOISE = range(9)

    @classmethod
    def validate_to_words(cls, words: list[str]) -> bool:
        if len(words) > 1 and MessageValue.from_name(words[1]) is not None:
            match MessageValue.from_name(words[1]):  # word[0] is the device name
                case MessageValue.CALL:
                    return len(words) == 3
                case MessageValue.INFO | MessageValue.CHANNEL:
                    return True
                case _: return len(words) == 2
        return False


class SystemValue(TalkieCode):
    BOARD, DROPS, DELAY, MUTE, SOCKET, TALKER, MANIFESTO = range(7)


class RogerValue(TalkieCode):
    ROGER, NEGATIVE, SAY_AGAIN, NIL = range(4)


class ErrorValue(TalkieCode):
    FROM, FIELD, CHECKSUM, MESSAGE, IDENTITY, DELAY, KEY, DATA = range(8)

