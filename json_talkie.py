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
from typing import Dict, Tuple, Any, TYPE_CHECKING, Callable
import time
import platform

from broadcast_socket import BroadcastSocket

from talkie_codes import JsonKey, SourceData, MessageData, SystemData, EchoData



class JsonTalkie:

    def __init__(self, socket: BroadcastSocket, manifesto: Dict[str, Dict[str, Any]], verbose: bool = False):
        self._socket: BroadcastSocket = socket  # Composition over inheritance
        self._manifesto: Dict[str, Dict[str, Any]] = manifesto
        self._channel: int = 0
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
                        if message[JsonKey.MESSAGE.value] == MessageData.ECHO.value:
                            if JsonKey.ORIGINAL.value in message:
                                original_message_code = MessageData(message[JsonKey.ORIGINAL.value])
                                match original_message_code:
                                    case MessageData.PING:
                                        out_time_ms: int = message[JsonKey.TIMESTAMP.value]
                                        actual_time: int = self.message_id()
                                        delay_ms: int = actual_time - out_time_ms
                                        if delay_ms < 0:    # do overflow as if uint16_t in c++
                                            delay_ms += 0xFFFF + 1  # 2^16
                                        message[JsonKey.VALUE.value] = delay_ms

                        if self._verbose:
                            print(message)
                        if JsonKey.FROM.value in message:
                            self._devices_address[message[ JsonKey.FROM.value ]] = ip_port

                        self.processMessage(message)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    if self._verbose:
                        print(f"\tInvalid message: {e}")
                    pass


    def remoteSend(self, message: Dict[str, Any]) -> bool:
        """Sends messages without network awareness."""
        message[ JsonKey.SOURCE.value ] = SourceData.REMOTE.value
        if message.get( JsonKey.FROM.value ) is not None:
            if message[JsonKey.FROM.value] != self._manifesto['talker']['name']:
                message[JsonKey.TO.value] = message[JsonKey.FROM.value]
                message[ JsonKey.FROM.value ] = self._manifesto['talker']['name']
        else:
            message[ JsonKey.FROM.value ] = self._manifesto['talker']['name']

        if JsonKey.IDENTITY.value not in message:
            message[ JsonKey.IDENTITY.value ] = JsonTalkie.message_id()
        JsonTalkie.valid_checksum(message)
        if self._verbose:
            print(message)
        # Avoids broadcasting flooding
        sent_result: bool = False
        if JsonKey.TO.value in message and message[ JsonKey.TO.value ] in self._devices_address:
            sent_result = self._socket.send( JsonTalkie.encode(message), self._devices_address[message[ JsonKey.TO.value ]] )
            if self._verbose:
                print("--> DIRECT SENDING -->")
        else:
            sent_result = self._socket.send( JsonTalkie.encode(message) )
            if self._verbose:
                print("--> BROADCAST SENDING -->")
        return sent_result
    

    def hereSend(self, message: Dict[str, Any]) -> bool:
        message[ JsonKey.SOURCE.value ] = SourceData.HERE.value
        return self.processMessage(message)
    

    def transmitMessage(self, message: Dict[str, Any]) -> bool:
        source_data = SourceData( message.get(JsonKey.SOURCE.value, SourceData.REMOTE) )   # get is safer than []
        match source_data:
            case SourceData.HERE:
                return self.hereSend(message)
            case _: # Default is remote
                return self.remoteSend(message)


    def processMessage(self, message: Dict[str, Any]) -> bool:
        """Handles message content only."""

        message_data = MessageData(message[JsonKey.MESSAGE.value])

        if message_data is not None:

            message[JsonKey.ORIGINAL.value] = message_data.value
            if message[JsonKey.MESSAGE.value] < MessageData.ECHO.value:
                message[JsonKey.MESSAGE.value] = MessageData.ECHO.value

            match message_data:

                case MessageData.RUN:
                    if JsonKey.NAME.value in message and 'run' in self._manifesto:
                        if message[JsonKey.NAME.value] in self._manifesto['run']:
                            self.transmitMessage(message)
                            roger: bool = self._manifesto['run'][message[JsonKey.NAME.value]]['function'](message)
                            if roger:
                                message[JsonKey.ROGER.value] = EchoData.ROGER
                            else:
                                message[JsonKey.ROGER.value] = EchoData.NEGATIVE
                            return self.transmitMessage(message)
                        else:
                            message[JsonKey.ROGER.value] = EchoData.SAY_AGAIN
                            self.transmitMessage(message)

                case MessageData.SET:
                    if JsonKey.VALUE.value in message and isinstance(message[JsonKey.VALUE.value], int) and JsonKey.NAME.value in message and 'set' in self._manifesto:
                        if message[JsonKey.NAME.value] in self._manifesto['set']:
                            self.transmitMessage(message)
                            roger: bool = self._manifesto['set'][message[JsonKey.NAME.value]]['function'](message, message[JsonKey.VALUE.value])
                            if roger:
                                message[JsonKey.ROGER.value] = EchoData.ROGER
                            else:
                                message[JsonKey.ROGER.value] = EchoData.NEGATIVE
                            return self.transmitMessage(message)
                        else:
                            message[JsonKey.ROGER.value] = EchoData.SAY_AGAIN
                            self.transmitMessage(message)

                case MessageData.GET:
                    if JsonKey.NAME.value in message and 'get' in self._manifesto:
                        if message[JsonKey.NAME.value] in self._manifesto['get']:
                            self.transmitMessage(message)
                            message[JsonKey.VALUE.value] = self._manifesto['get'][message[JsonKey.NAME.value]]['function'](message)
                            return self.transmitMessage(message)
                        else:
                            message[JsonKey.ROGER.value] = EchoData.SAY_AGAIN
                            self.transmitMessage(message)

                case MessageData.TALK:
                    message[JsonKey.DESCRIPTION.value] = f"{self._manifesto['talker']['description']}"
                    return self.transmitMessage(message)
                
                case MessageData.LIST:
                    if 'run' in self._manifesto:
                        for name, content in self._manifesto['run'].items():
                            message[JsonKey.NAME.value] = name
                            message[JsonKey.DESCRIPTION.value] = content['description']
                            self.transmitMessage(message)
                    if 'set' in self._manifesto:
                        for name, content in self._manifesto['set'].items():
                            message[JsonKey.NAME.value] = name
                            message[JsonKey.DESCRIPTION.value] = content['description']
                            self.transmitMessage(message)
                    if 'get' in self._manifesto:
                        for name, content in self._manifesto['get'].items():
                            message[JsonKey.NAME.value] = name
                            message[JsonKey.DESCRIPTION.value] = content['description']
                            self.transmitMessage(message)
                    return True
                
                case MessageData.CHANNEL:
                    if JsonKey.VALUE.value in message and isinstance(message[JsonKey.VALUE.value], int):
                        self._channel = message[JsonKey.VALUE.value]
                    else:
                        message[JsonKey.VALUE.value] = self._channel
                    return self.transmitMessage(message)
                
                case MessageData.SYS:
                    message[JsonKey.DESCRIPTION.value] = f"{platform.platform()}"
                    return self.transmitMessage(message)
                
                case MessageData.ECHO:

                    # Echo codes (g):
                    #     0 - ROGER
                    #     1 - UNKNOWN
                    #     2 - NONE

                    if "echo" in self._manifesto:
                        self._manifesto["echo"](message)

                case MessageData.ERROR:

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
        if isinstance(message, dict) and JsonKey.CHECKSUM.value in message:
            if JsonTalkie.valid_checksum(message):
                if JsonKey.MESSAGE.value not in message:
                    return False
                if not isinstance(message[JsonKey.MESSAGE.value], int):
                    return False
                if not (JsonKey.FROM.value in message and JsonKey.IDENTITY.value in message):
                    return False
                if JsonKey.TO.value in message:
                    if isinstance(message[ JsonKey.TO.value ], int):
                        if message[ JsonKey.TO.value ] != self._channel:
                            return False
                    elif message[ JsonKey.TO.value ] != self._manifesto['talker']['name']:
                        return False
            else:
                return False
        else:
            return False
        message[JsonKey.CHECKSUM.value] = SourceData.REMOTE.value
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
        if JsonKey.CHECKSUM.value in message:
            message_checksum = message[ JsonKey.CHECKSUM.value ]
        message[ JsonKey.CHECKSUM.value ] = 0
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
        message[ JsonKey.CHECKSUM.value ] = checksum
        return message_checksum == checksum

