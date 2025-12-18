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
from enum import Enum
from typing import Union, cast, Optional


class JsonKey(Enum):
    SOURCE      = "c"
    CHECKSUM    = "c"
    TIMESTAMP   = "i"
    IDENTITY    = "i"
    MESSAGE     = "m"
    ORIGINAL    = "o"
    FROM        = "f"
    TO          = "t"
    SYSTEM      = "s"
    ERROR       = "e"
    VALUE       = "v"
    REPLY       = "r"
    ROGER       = "g"
    ACTION      = "a"
    NAME        = "n"
    INDEX       = "x"
    DESCRIPTION = "d"


class TalkieCode:
    """Mixin with shared functionality for Talkie codes (enums)"""

    def __str__(self) -> str:
        """String representation is lowercase"""
                # Tell type checker self is an Enum
        enum_self = cast(Enum, self)
        return enum_self.name.lower()
    
    @classmethod
    def from_name(cls, name: str) -> Union['Enum', None]:
        """Returns the TalkieCode based on a lower case name"""
        try:
            return cls[name.upper()]    # TalkieCode is in upper case
        except KeyError:
            return None


class SourceData(TalkieCode, Enum):
    REMOTE, LOCAL, HERE = range(3)


class MessageData(TalkieCode, Enum):
    RUN, SET, GET, LIST, SYS, TALK, CHANNEL, PING, ECHO, ERROR = range(10)

    @classmethod
    def validate_to_words(cls, words: list[str]) -> bool:
        if len(words) > 1 and MessageData.from_name(words[1]):
            match MessageData.from_name(words[1]):  # word[0] is the device name
                case MessageData.RUN | MessageData.GET:
                    return len(words) == 3
                case MessageData.SET: return len(words) == 4
                case MessageData.SYS | MessageData.CHANNEL:
                    return True
                case _: return len(words) == 2
        return False


class SystemData(TalkieCode, Enum):
    BOARD, DROPS, DELAY, MUTE, UNMUTE, MUTED, SOCKET, TALKER, MANIFESTO = range(9)


class EchoData(TalkieCode, Enum):
    ROGER, SAY_AGAIN, NEGATIVE, NIL = range(4)


class ErrorData(TalkieCode, Enum):
    FROM, FIELD, CHECKSUM, MESSAGE, IDENTITY, DELAY, KEY, DATA = range(8)

