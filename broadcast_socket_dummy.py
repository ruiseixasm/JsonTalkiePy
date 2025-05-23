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
import socket
import json
import threading
import uuid
import random
import time
from typing import Optional, Tuple, Any, Dict

from broadcast_socket import BroadcastSocket

class BroadcastSocket_Dummy(BroadcastSocket):
    """Dummy broadcast socket with explicit lifecycle control."""
    
    def __init__(self, port: int = 5005):
        super().__init__()
        self._port = port
        self._socket = None  # Not initialized until open()
        self._time: float = time.time()
        self._sent_message: Dict[str, Any] = {}
    
    def open(self) -> bool:
        """Initialize and bind the socket."""
        try:
            divide: float = 1/random.randint(0, 1000)
            self._socket = True
            return True
        except Exception as e:
            print(f"Socket open failed: {e}")
            return False
    
    def close(self):
        """Release socket resources."""
        if self._socket:
            self._socket = None
    
    
    def set_port(self, new_port: int) -> bool:
        """Change port and immediately rebind the socket.
        Returns True if successful, False if failed to rebind.
        """
        if not 1 <= new_port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        self._port = new_port
        return True
            
    def get_port(self) -> int:
        """Returns current port number"""
        return self._port


    def send(self, data: bytes, device_address: Tuple[str, int] = None) -> bool:
        """Broadcast data if socket is active."""
        if not self._socket:
            return False
        try:
            divide: float = 1/random.randint(0, 1000)
            print(f"DUMMY SENT: {data}")
            message: Dict[str, Any] = BroadcastSocket_Dummy.decode(data)
            self._sent_message = message
            return True
        except Exception as e:
            print(f"DUMMY Send failed: {e}")
            return False
    
    def receive(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        """Non-blocking receive."""
        if not self._socket:
            return None
        try:
            if time.time() - self._time > 1:
                self._time = time.time()
                random_number: int = random.randint(0, 1000)
                if random.randint(0, 1000) < 10:
                    divide: float = 1/random_number
                    message = self.messages[random_number % len(self.messages)]
                    message["i"] = BroadcastSocket_Dummy.message_id()
                    BroadcastSocket_Dummy.valid_checksum(message)
                    data = BroadcastSocket_Dummy.encode(message)
                    print(f"DUMMY RECEIVED: {data}")
                    data_tuple = (data, ('192.168.31.22', 5005))
                    return data_tuple
            return None
        except BlockingIOError:
            return None
        except Exception as e:
            print(f"DUMMY Receive error: {e}")
            return None

    messages: tuple[Dict[str, Any]] = (
        {"m": "run", "w": "buzz", "t": "Buzzer", "f": "Buzzer", "i": "bc40fd17"},
        {"m": "echo", "t": "Buzzer", "i": "bc40fd17", "r": "[Buzzer buzz]\\tCalled", "f": "Buzzer"},
        {"m": "talk", "f": "Dummy", "i": "dce4fac7"},
        {"m": "echo", "t": "Talker-a6", "i": "dce4fac7", "r": "[Talker-a6]\\tA simple Talker!", "f": "Talker-a6"}
    )

    @staticmethod
    def message_id() -> int:
        """Generates a 32-bit wrapped timestamp ID using overflow."""
        return int(time.time() * 1000) & 0xFFFFFFFF
    
    @staticmethod
    def encode(message: Dict[str, Any]) -> bytes:
        return json.dumps(message, separators=(',', ':')).encode('utf-8')

    @staticmethod
    def decode(data: bytes) -> Dict[str, Any]:
        return json.loads(data.decode('utf-8'))

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
