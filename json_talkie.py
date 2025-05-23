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

DEBUG = False  # Set to False to disable debug prints

# Keys:
#     b: byte
#     c: checksum
#     d: description
#     e: error code
#     f: from
#     g: echo roger code
#     i: id
#     m: message
#     n: name
#     r: reply
#     t: to
#     v: value
#     w: what

# Messages/Whats:
#     0 talk
#     1 list
#     2 run
#     3 set
#     4 get
#     5 sys
#     6 echo
#     7 error

# Echo codes (g):
#     0 - ROGER
#     1 - UNKNOWN
#     2 - NONE

# Error types (e):
#     0 - Unknown sender
#     1 - Message missing the checksum
#     2 - Message corrupted
#     3 - Wrong message code
#     4 - Message NOT identified
#     5 - Set command arrived too late



class JsonTalkie:

    def __init__(self, socket: BroadcastSocket, manifesto: Dict[str, Dict[str, Any]]):
        self._socket: BroadcastSocket = socket  # Composition over inheritance
        self._manifesto: Dict[str, Dict[str, Any]] = manifesto
        self._channel: int = 0
        self._message_time: float = 0.0
        self._running: bool = False
        self._devices_address: Dict[str, Tuple[str, int]] = {}

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

    def talk(self, message: Dict[str, Any]) -> bool:
        """Sends messages without network awareness."""
        message["f"] = self._manifesto['talker']['name']
        if "i" not in message:
            message["i"] = JsonTalkie.message_id()
        JsonTalkie.valid_checksum(message)
        if DEBUG:
            print(message)
        # Avoids broadcasting flooding (no need to check for "*", never kept in the devices_address)
        if "t" in message and message["t"] in self._devices_address:
            return self._socket.send( JsonTalkie.encode(message), self._devices_address[message["t"]] )
        return self._socket.send( JsonTalkie.encode(message) )
    
    def listen(self):
        """Processes raw bytes from socket."""
        while self._running:
            received = self._socket.receive()
            if received:
                data, ip_port = received  # Explicitly ignore (ip, port)
                try:
                    if DEBUG:
                        print(data)
                    message: Dict[str, Any] = JsonTalkie.decode(data)
                    if self.validate_message(message):
                        if DEBUG:
                            print(message)
                        if "f" in message and message["f"] != "*":
                            self._devices_address[message["f"]] = ip_port
                        self.receive(message)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    if DEBUG:
                        print(f"\tInvalid message: {e}")
                    pass

    def receive(self, message: Dict[str, Any]) -> bool:
        """Handles message content only."""
        message["t"] = message["f"]
        match message["m"]:
            case 0:         # talk
                message["w"] = 0
                message["m"] = 6
                message["d"] = f"{self._manifesto['talker']['description']}"
                return self.talk(message)
            case 1:         # list
                message["m"] = 6
                if 'run' in self._manifesto:
                    message["w"] = 2
                    for name, content in self._manifesto['run'].items():
                        message["n"] = name
                        message["d"] = content['description']
                        self.talk(message)
                if 'set' in self._manifesto:
                    message["w"] = 3
                    for name, content in self._manifesto['set'].items():
                        message["n"] = name
                        message["d"] = content['description']
                        self.talk(message)
                if 'get' in self._manifesto:
                    message["w"] = 4
                    for name, content in self._manifesto['get'].items():
                        message["n"] = name
                        message["d"] = content['description']
                        self.talk(message)
                return True
            case 2:         # run
                message["w"] = 2
                message["m"] = 6
                if "n" in message and 'run' in self._manifesto:
                    if message["n"] in self._manifesto['run']:
                        message["r"] = "ROGER"
                        self.talk(message)
                        roger: bool = self._manifesto['run'][message["n"]]['function'](message)
                        if roger:
                            message["r"] = "ROGER"
                        else:
                            message["r"] = "FAIL"
                        return self.talk(message)
                    else:
                        message["r"] = "UNKNOWN"
                        self.talk(message)
            case 3:         # set
                message["w"] = 3
                message["m"] = 6
                if "v" in message and isinstance(message["v"], int) and "n" in message and 'set' in self._manifesto:
                    if message["n"] in self._manifesto['set']:
                        message["r"] = "ROGER"
                        self.talk(message)
                        roger: bool = self._manifesto['set'][message["n"]]['function'](message, message["v"])
                        if roger:
                            message["r"] = "ROGER"
                        else:
                            message["r"] = "FAIL"
                        return self.talk(message)
                    else:
                        message["r"] = "UNKNOWN"
                        self.talk(message)
            case 4:         # get
                message["w"] = 4
                message["m"] = 6
                if "n" in message and 'get' in self._manifesto:
                    if message["n"] in self._manifesto['get']:
                        message["r"] = "ROGER"
                        self.talk(message)
                        message["r"] = "ROGER"
                        message["v"] = self._manifesto['get'][message["n"]]['function'](message)
                        return self.talk(message)
                    else:
                        message["r"] = "UNKNOWN"
                        self.talk(message)
            case 5:         # sys
                message["w"] = 5
                message["m"] = 6
                message["d"] = f"{platform.platform()}"
                return self.talk(message)
            case 6:         # echo

                # Echo codes (g):
                #     0 - ROGER
                #     1 - UNKNOWN
                #     2 - NONE

                if "echo" in self._manifesto:
                    self._manifesto["echo"](message)
            case 7:         # error

                # Error types:
                #     0 - Unknown sender
                #     1 - Message missing the checksum
                #     2 - Message corrupted
                #     3 - Wrong message code
                #     4 - Message NOT identified
                #     5 - Set command arrived too late

                if "error" in self._manifesto:
                    self._manifesto["error"](message)
            case 8:         # channel
                if "b" in message and isinstance(message["b"], int):
                    self._channel = message["b"]
                message["m"] = 6
                message["w"] = 8
                message["b"] = self._channel
                return self.talk(message)
            case _:
                print("\tUnknown message!")
        return False


    def validate_message(self, message: Dict[str, Any]) -> bool:
        if isinstance(message, dict) and "c" in message:
            try:
                message_checksum: int = int(message.get("c", None))
            except (ValueError, TypeError):
                return False
            if JsonTalkie.valid_checksum(message):
                if "m" not in message:
                    return False
                if not isinstance(message["m"], int):
                    return False
                if not ("f" in message and "i" in message):
                    return False
                if not (message["m"] == 0 or message["m"] == 5):
                    if "t" not in message:
                        return False
                    if message["t"] != "*":
                        if isinstance(message["t"], int):
                            if message["t"] != self._channel:
                                return False
                        elif message["t"] != self._manifesto['talker']['name']:
                            return False
            else:
                return False
        else:
            return False
        return True


    @staticmethod
    def message_id() -> int:
        """Generates a 32-bit wrapped timestamp ID using overflow."""
        return int(time.time() * 1000) & 0xFFFFFFFF
    
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
        if "c" in message:
            message_checksum = message["c"]
        message["c"] = 0
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
        message["c"] = checksum
        return message_checksum == checksum

