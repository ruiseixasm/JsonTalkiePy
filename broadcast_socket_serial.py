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
        self._reading_serial = False
        self._received_buffer = bytearray(128)
        self._received_length = 0
    
    def open(self) -> bool:
        """Initialize and bind the socket."""
        try:
            self._socket = serial.Serial(
                port=self._port,
                baudrate=115200,
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
        if not self._socket:
            return None

        try:
            while self._socket.in_waiting > 0:
                c = self._socket.read(1)
                if not c:
                    break

                c = c[0]  # int 0–255

                if self._reading_serial:
                    if self._received_length < self.BROADCAST_SOCKET_BUFFER_SIZE:
                        if (
                            c == ord('}')
                            and self._received_length
                            and self._received_buffer[self._received_length - 1] != ord('\\')
                        ):
                            self._reading_serial = False
                            self._received_buffer[self._received_length] = c
                            self._received_length += 1

                            data = bytes(self._received_buffer[:self._received_length])
                            self._received_length = 0
                            return (data, None)
                        else:
                            self._received_buffer[self._received_length] = c
                            self._received_length += 1
                    else:
                        self._reading_serial = False
                        self._received_length = 0  # overflow → reset

                elif c == ord('{'):
                    self._reading_serial = True
                    self._received_length = 0
                    self._received_buffer[self._received_length] = c
                    self._received_length += 1

            return None

        except Exception:
            # Only truly unexpected failures land here
            self._reading_serial = False
            self._received_length = 0
            return None

        
    # def receive(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
    #     """Non-blocking receive."""
    #     if not self._socket:
    #         return None
    #     try:
    #         data: bytes = self._socket.readline()
    #         if data:
    #             return (data, None) # As data_tuple
    #         return None
    #     except BlockingIOError:
    #         return None
    #     except Exception as e:
    #         print(f"Receive error: {e}")
    #         return None

