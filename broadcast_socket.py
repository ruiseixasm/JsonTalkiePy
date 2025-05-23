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
from typing import Optional, Tuple, Dict

class BroadcastSocket:
    def __init__(self, *parameters):
        self._port = 5005
        self._socket = None  # Not initialized until open()
    
    def open(self) -> bool:
        """Initialize and bind the socket."""
        return False
    
    def close(self):
        """Release socket resources."""
        return True
    

    def set_port(self, new_port: int) -> bool:
        """Change port and immediately rebind the socket.
        Returns True if successful, False if failed to rebind.
        """
        return True
            
    def get_port(self) -> int:
        """Returns current port number"""
        return self._port


    def send(self, data: bytes, device_address: Tuple[str, int] = None) -> bool:
        """Broadcast data if socket is active."""
        return False
    
    def receive(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        return None
        

