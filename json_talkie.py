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
import json
import threading
import uuid
from typing import Dict, Tuple, Any, TYPE_CHECKING, Callable, Union
import time
import platform

from broadcast_socket import BroadcastSocket

from talkie_codes import TalkieKey, SourceValue, MessageValue, SystemValue, RogerValue



class JsonTalkie:

    def __init__(self, socket: BroadcastSocket, manifesto: Dict[str, Dict[str, Any]], verbose: bool = False):
        self._socket: BroadcastSocket = socket  # Composition over inheritance
        self._manifesto: Dict[str, Dict[str, Any]] = manifesto
        self._channel: int = 0
        self._original_message: Dict[str, Any] = {}
        self._received_message_data: MessageValue = MessageValue.NOISE
        self._verbose: bool = verbose
        # State variables
        self._devices_address: Dict[str, Tuple[str, int]] = {}
        self._message_time: float = 0.0
        self._running: bool = False

    def on(self) -> bool:
        """Start message processing (no network knowledge)."""
        if not self._socket.open():
            return False
        self._running = True
        self._thread = threading.Thread(target=self.listen, daemon=True)    # Where the listen is set
        self._thread.start()
        return True
    
    def off(self):
        """Stop processing (delegates cleanup to socket)."""
        self._running = False
        self._receiver = None
        if hasattr(self, '_thread'):
            self._thread.join()
        self._socket.close()

    @staticmethod
    def getMessageData(message: Dict[str, Any], json_key: TalkieKey) -> Union[MessageValue, None]:
        message_data = message.get(json_key.value)
        if message_data is not None:
            return MessageValue(message_data)
        return None


    def listen(self):
        """Processes raw bytes from socket."""
        while self._running:
            received = self._socket.receive()
            if received:
                data, ip_port = received  # Explicitly ignore (ip, port)
                try:
                    if self._verbose:
                        print(data)
                    message: Dict[str, Any] = JsonTalkie.decode(data)
                    if self.validate_message(message):
                        # Add info to echo message right away accordingly to the message original type
                        if message[TalkieKey.MESSAGE.value] == MessageValue.ECHO.value:
                            match JsonTalkie.getMessageData(self._original_message, TalkieKey.MESSAGE):
                                case MessageValue.PING:
                                    actual_time: int = self.message_id()
                                    out_time_ms: int = message[TalkieKey.TIMESTAMP.value]
                                    delay_ms: int = actual_time - out_time_ms
                                    if delay_ms < 0:    # do overflow as if uint16_t in c++
                                        delay_ms += 0xFFFF + 1  # 2^16
                                    if str(0) not in message:  # Don't change value already set
                                        message[ str(0) ] = delay_ms

                        if self._verbose:
                            print(message)
                        if TalkieKey.FROM.value in message:
                            self._devices_address[message[ TalkieKey.FROM.value ]] = ip_port

                        self.processMessage(message)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    if self._verbose:
                        print(f"\tInvalid message: {e}")
                    pass


    def remoteSend(self, message: Dict[str, Any]) -> bool:
        """Sends messages without network awareness."""
        message[ TalkieKey.SOURCE.value ] = SourceValue.REMOTE.value
        if message.get( TalkieKey.FROM.value ) is not None:
            if message[TalkieKey.FROM.value] != self._manifesto['talker']['name']:
                message[TalkieKey.TO.value] = message[TalkieKey.FROM.value]
                message[ TalkieKey.FROM.value ] = self._manifesto['talker']['name']
        else:
            message[ TalkieKey.FROM.value ] = self._manifesto['talker']['name']

        if TalkieKey.IDENTITY.value not in message:
            message[ TalkieKey.IDENTITY.value ] = JsonTalkie.message_id()
            if message[TalkieKey.MESSAGE.value] < MessageValue.ECHO.value:
                self._original_message = message
        JsonTalkie.valid_checksum(message)
        if self._verbose:
            print(message)
        # Avoids broadcasting flooding
        sent_result: bool = False
        if TalkieKey.TO.value in message and message[ TalkieKey.TO.value ] in self._devices_address:
            sent_result = self._socket.send( JsonTalkie.encode(message), self._devices_address[message[ TalkieKey.TO.value ]] )
            if self._verbose:
                print("--> DIRECT SENDING -->")
        else:
            sent_result = self._socket.send( JsonTalkie.encode(message) )
            if self._verbose:
                print("--> BROADCAST SENDING -->")
        return sent_result
    

    def hereSend(self, message: Dict[str, Any]) -> bool:
        message[ TalkieKey.SOURCE.value ] = SourceValue.HERE.value
        return self.processMessage(message)
    

    def transmitMessage(self, message: Dict[str, Any]) -> bool:
        source_data = SourceValue( message.get(TalkieKey.SOURCE.value, SourceValue.REMOTE) )   # get is safer than []
        match source_data:
            case SourceValue.HERE:
                return self.hereSend(message)
            case _: # Default is remote
                return self.remoteSend(message)


    def processMessage(self, message: Dict[str, Any]) -> bool:
        """Handles message content only."""

        message_data = MessageValue(message[TalkieKey.MESSAGE.value])

        if message_data is not None:

            if message[TalkieKey.MESSAGE.value] < MessageValue.ECHO.value:
                self._received_message_data = MessageValue(message[TalkieKey.MESSAGE.value])
                message[TalkieKey.MESSAGE.value] = MessageValue.ECHO.value

            match message_data:

                case MessageValue.CALL:
                    if TalkieKey.ACTION.value in message and 'run' in self._manifesto:
                        if message[TalkieKey.ACTION.value] in self._manifesto['run']:
                            self.transmitMessage(message)
                            roger: bool = self._manifesto['run'][message[TalkieKey.ACTION.value]]['function'](message)
                            if roger:
                                message[TalkieKey.ROGER.value] = RogerValue.ROGER
                            else:
                                message[TalkieKey.ROGER.value] = RogerValue.NEGATIVE
                            return self.transmitMessage(message)
                        else:
                            message[TalkieKey.ROGER.value] = RogerValue.SAY_AGAIN
                            self.transmitMessage(message)

                case MessageValue.LIST:
                    if 'run' in self._manifesto:
                        for name, content in self._manifesto['run'].items():
                            message[TalkieKey.ACTION.value] = name
                            message[ str(0) ] = content['description']
                            self.transmitMessage(message)
                    if 'set' in self._manifesto:
                        for name, content in self._manifesto['set'].items():
                            message[TalkieKey.ACTION.value] = name
                            message[ str(0) ] = content['description']
                            self.transmitMessage(message)
                    if 'get' in self._manifesto:
                        for name, content in self._manifesto['get'].items():
                            message[TalkieKey.ACTION.value] = name
                            message[ str(0) ] = content['description']
                            self.transmitMessage(message)
                    return True
                
                case MessageValue.TALK:
                    message[ str(0) ] = f"{self._manifesto['talker']['description']}"
                    return self.transmitMessage(message)
                
                case MessageValue.CHANNEL:
                    if TalkieKey.VALUE.value in message and isinstance(message[TalkieKey.VALUE.value], int):
                        self._channel = message[TalkieKey.VALUE.value]
                    else:
                        message[TalkieKey.VALUE.value] = self._channel
                    return self.transmitMessage(message)
                
                case MessageValue.PING:
                    # Does nothing, sends it right away
                    return self.transmitMessage(message)
                
                case MessageValue.SYS:
                    message[ str(0) ] = f"{platform.platform()}"
                    return self.transmitMessage(message)
                
                case MessageValue.ECHO:

                    # Echo codes (g):
                    #     0 - ROGER
                    #     1 - UNKNOWN
                    #     2 - NONE

                    if "echo" in self._manifesto:
                        message_id = message[TalkieKey.IDENTITY.value]
                        if message_id == self._original_message.get(TalkieKey.IDENTITY.value):
                            self._manifesto["echo"](message)

                case MessageValue.ERROR:

                    # Error types:
                    #     0 - Unknown sender
                    #     1 - Message missing the checksum
                    #     2 - Message corrupted
                    #     3 - Wrong message code
                    #     4 - Message NOT identified
                    #     5 - Set command arrived too late

                    if "error" in self._manifesto:
                        self._manifesto["error"](message)

                case _:
                    print("\tUnknown message!")
        return False


    def validate_message(self, message: Dict[str, Any]) -> bool:
        if isinstance(message, dict) and TalkieKey.CHECKSUM.value in message:
            if JsonTalkie.valid_checksum(message):
                if TalkieKey.MESSAGE.value not in message:
                    return False
                if not isinstance(message[TalkieKey.MESSAGE.value], int):
                    return False
                if not (TalkieKey.FROM.value in message and TalkieKey.IDENTITY.value in message):
                    return False
                if TalkieKey.TO.value in message:
                    if isinstance(message[ TalkieKey.TO.value ], int):
                        if message[ TalkieKey.TO.value ] != self._channel:
                            return False
                    elif message[ TalkieKey.TO.value ] != self._manifesto['talker']['name']:
                        return False
            else:
                return False
        else:
            return False
        message[TalkieKey.CHECKSUM.value] = SourceValue.REMOTE.value
        return True


    @staticmethod
    def message_id() -> int:
        """Generates a 16-bit wrapped timestamp ID using overflow."""
        return int(time.time() * 1000) & 0xFFFF # Truncated to 16 bits (uint16_t)
    
    @staticmethod
    def encode(message: Dict[str, Any]) -> bytes:
        # If specified, separators should be an (item_separator, key_separator)
        #     tuple. The default is (', ', ': ') if indent is None and
        #     (',', ': ') otherwise. To get the most compact JSON representation,
        #     you should specify (',', ':') to eliminate whitespace.
        return json.dumps(message, separators=(',', ':')).encode('utf-8')

    @staticmethod
    def decode(data: bytes) -> Dict[str, Any]:
        data_str = data.decode('utf-8')
        try:
            data_dict = json.loads(data_str)
            return data_dict
        except (json.JSONDecodeError):
            return None

    @staticmethod
    def valid_checksum(message: Dict[str, Any]) -> bool:
        # If specified, separators should be an (item_separator, key_separator)
        #     tuple. The default is (', ', ': ') if indent is None and
        #     (',', ': ') otherwise. To get the most compact JSON representation,
        #     you should specify (',', ':') to eliminate whitespace.
        message_checksum: int = 0
        if TalkieKey.CHECKSUM.value in message:
            message_checksum = message[ TalkieKey.CHECKSUM.value ]
        message[ TalkieKey.CHECKSUM.value ] = 0
        data = json.dumps(message, separators=(',', ':')).encode('utf-8')
        # 16-bit word and XORing
        checksum = 0
        for i in range(0, len(data), 2):
            # Combine two bytes into 16-bit value
            chunk = data[i] << 8
            if i+1 < len(data):
                chunk |= data[i+1]
            checksum ^= chunk
        checksum &= 0xFFFF
        message[ TalkieKey.CHECKSUM.value ] = checksum
        return message_checksum == checksum

