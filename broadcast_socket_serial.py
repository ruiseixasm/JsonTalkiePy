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

    BROADCAST_SOCKET_BUFFER_SIZE = 128
    DEFAULT_BAUDRATE = 115200
    DEFAULT_TIMEOUT = 1.0  # seconds
    
    
    def __init__(self, port: str = 'COM5', baudrate: int = None, timeout: float = None):
        """
        Initialize serial broadcast socket.
        
        Args:
            port: Serial port (e.g., 'COM5', '/dev/ttyUSB0')
            baudrate: Baud rate for serial communication (default: 115200)
            timeout: Read timeout in seconds (default: 1.0)
        """
        super().__init__()
        self._port = port
        self._baudrate = baudrate or self.DEFAULT_BAUDRATE
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._socket = None  # Not initialized until open()
        self._reading_serial = False
        self._received_buffer = bytearray(self.BROADCAST_SOCKET_BUFFER_SIZE)
        self._received_length = 0


    def __str__(self) -> str:
        status = "open" if self.is_open() else "closed"
        return f"BroadcastSocket_Serial(port={self._port}, baud={self._baudrate}, status={status})"


    def open(self) -> bool:
        """Initialize and bind the socket."""
        try:
            self._socket = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout,
                write_timeout=self._timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
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


    def set_baudrate(self, baudrate: int) -> bool:
        """Change baud rate and reopen connection.
        
        Args:
            baudrate: New baud rate (e.g., 9600, 115200, 57600)
        
        Returns:
            True if successful, False if failed to reopen.
        """
        # Close existing connection if open
        was_open = self._socket and self._socket.is_open
        if was_open:
            self.close()

        old_baud = self._baudrate
        self._baudrate = baudrate

        # Reopen if it was previously open
        if was_open:
            success = self.open()
            if success:
                print(f"Changed baudrate from {old_baud} to {baudrate}")
            else:
                print(f"Failed to reopen at {baudrate} baud, reverting to {old_baud}")
                self._baudrate = old_baud
                self.open()  # Try to reopen with old baudrate
            return success
        return True
    

    def get_baudrate(self) -> int:
        return self._baudrate
    

    def get_timeout(self) -> float:
        return self._timeout
    

    def get_settings(self) -> dict:
        return {
            'port': self._port,
            'baudrate': self._baudrate,
            'timeout': self._timeout,
            'is_open': self._socket.is_open if self._socket else False
        }
    

    def set_port(self, new_port: int) -> bool:
        """Change serial port and reopen connection.
        
        Args:
            new_port: New serial port (e.g., 'COM3', '/dev/ttyUSB1')
        
        Returns:
            True if successful, False if failed to reopen.
        """
        # Close existing connection if open
        was_open = self._socket and self._socket.is_open
        if was_open:
            self.close()

        old_port = self._port
        self._port = new_port

        # Reopen if it was previously open
        if was_open:
            success = self.open()
            if success:
                print(f"Changed serial port from {old_port} to {new_port}")
            else:
                print(f"Failed to reopen serial port {new_port}, reverting to {old_port}")
                self._port = old_port
                self.open()  # Try to reopen old port
            return success
        return True


    def get_port(self) -> int:
        """Returns current port number"""
        return self._port


    def flush(self):
        if self._socket and self._socket.is_open:
            self._socket.reset_input_buffer()
            self._socket.reset_output_buffer()


    def is_open(self) -> bool:
        return self._socket is not None and self._socket.is_open


    def send(self, data: bytes, device_address: Tuple[str, int] = None) -> bool:
        """Send data through serial port.
        
        Args:
            data: Bytes to send
            device_address: Ignored for serial (kept for interface compatibility)
        
        Returns:
            True if successful, False if failed.
        """
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

        
