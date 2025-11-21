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
from typing import Optional, Tuple, Dict

DEBUG = False  # Set to False to disable debug prints

from broadcast_socket import BroadcastSocket

class BroadcastSocket_UDP(BroadcastSocket):
    """UDP broadcast socket with explicit lifecycle control."""
    
    def __init__(self, port: int = 5005):
        super().__init__()
        self._port = port
        self._socket = None  # Not initialized until open()
    
    def open(self) -> bool:
        """Initialize and bind the socket."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Critical!
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._socket.bind(('', self._port))
            self._socket.setblocking(False)
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
        """Safely change port with proper socket cleanup.
        Returns True if successful, False if failed (keeps old port).
        """
        if not 1 <= new_port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        if not self._socket:  # No active socket? Just update port
            self._port = new_port
            return True
            
        try:
            # 1. Create new socket first (don't touch old one yet)
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            new_socket.bind(('', new_port))
            new_socket.setblocking(False)
            
            # 2. Only now close old socket (with error protection)
            try:
                if self._socket:
                    self._socket.close()
            except OSError as e:
                print(f"Old socket close warning: {e}")
                # Continue anyway - we already have the new socket
            
            # 3. Commit the change
            self._socket = new_socket
            self._port = new_port
            return True
            
        except Exception as e:
            print(f"Port change failed: {e}")
            # Ensure new socket is closed if something went wrong
            if 'new_socket' in locals():
                new_socket.close()
            return False  # Keep original port/socket
    
    def get_port(self) -> int:
        """Returns current port number"""
        return self._port


    def send(self, data: bytes, device_address: Tuple[str, int] = None) -> bool:
        """Broadcast data if socket is active."""
        if DEBUG:
            print(f"Socket send data: {data} to address {device_address}")
        if not self._socket:
            return False
        try:
            if device_address:
                self._socket.sendto(data, device_address)
            else:
                self._socket.sendto(data, ('255.255.255.255', self._port))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def receive(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        """Non-blocking receive."""
        if not self._socket:
            return None
        try:
            data_ip_port: Optional[Tuple[bytes, Tuple[str, int]]] = self._socket.recvfrom(4096)
            if data_ip_port is not None and data_ip_port[1][1] == self._port:
                return data_ip_port
            return None
        except BlockingIOError:
            return None
        except Exception as e:
            print(f"Receive error: {e}")
            return None
        

