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
import serial   # python -m pip install pyserial
import serial.tools.list_ports
import time
from typing import Optional, Tuple, Any, Dict

from broadcast_socket import BroadcastSocket

class BroadcastSocket_Serial(BroadcastSocket):
    """Dummy broadcast socket with explicit lifecycle control."""
    
    def __init__(self, port: str = 'COM4'):
        super().__init__()
        self._port = port
        self._socket = None  # Not initialized until open()
    
    def open(self) -> bool:
        """Initialize and bind the socket."""
        try:
            self._socket = serial.Serial(
                port=self._port,
                baudrate=9600,
                timeout=1   # seconds
            )
            return True
        except Exception as e:
            print(f"Socket open failed: {e}")
            return False
    
    def close(self):
        """Release socket resources."""
        if self._socket:
            self._socket.close()
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
            self._socket.write(data)  # Send with newline
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def receive(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        """Non-blocking receive."""
        if not self._socket:
            return None
        try:
            data: bytes = self._socket.readline()
            if data:
                return (data, None) # As data_tuple
            return None
        except BlockingIOError:
            return None
        except Exception as e:
            print(f"Receive error: {e}")
            return None

