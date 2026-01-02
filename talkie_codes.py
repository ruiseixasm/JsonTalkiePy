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
    BROADCAST   = "b"
    CHECKSUM    = "c"
    TIMESTAMP   = "i"
    IDENTITY    = "i"
    MESSAGE     = "m"
    FROM        = "f"
    TO          = "t"
    SYSTEM      = "s"
    ACTION      = "a"
    ROGER       = "r"
    ERROR       = "e"


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


class ValueType(TalkieCode):
    STRING, INTEGER, OTHER, VOID = range(4)


class LinkType(TalkieCode):
    NONE, DOWN_LINKED, UP_LINKED, UP_BRIDGED = range(4)


class TalkerMatch(TalkieCode):
    NONE, ANY, BY_CHANNEL, BY_NAME, FAIL = range(5)


class BroadcastValue(TalkieCode):
    REMOTE, LOCAL, SELF, NONE = range(4)


class MessageValue(TalkieCode):
    TALK, CHANNEL, PING, CALL, LIST, SYSTEM, ECHO, ERROR, NOISE = range(9)

    @classmethod
    def validate_to_words(cls, words: list[str]) -> bool:
        if len(words) > 1 and MessageValue.from_name(words[1]) is not None:
            match MessageValue.from_name(words[1]):  # word[0] is the device name
                case MessageValue.CALL:
                    return len(words) == 3
                case MessageValue.SYSTEM | MessageValue.CHANNEL:
                    return True
                case _: return len(words) == 2
        return False


class SystemValue(TalkieCode):
    BOARD, MUTE, DROPS, DELAY, SOCKET, MANIFESTO, UNDEFINED = range(7)


class RogerValue(TalkieCode):
    ROGER, NEGATIVE, SAY_AGAIN, NIL, NO_JOY = range(5)


class ErrorValue(TalkieCode):
    CHECKSUM, MESSAGE, IDENTITY, FIELD, FROM, TO, DELAY, KEY, VALUE, UNDEFINED = range(10)

