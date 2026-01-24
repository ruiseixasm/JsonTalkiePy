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
from enum import Enum, IntEnum

from broadcast_socket import BroadcastSocket

from talkie_codes import TalkieKey, BroadcastValue, MessageValue, SystemValue, RogerValue, ErrorValue



class JsonTalkie:

    def __init__(self, socket: BroadcastSocket, manifesto: Dict[str, Dict[str, Any]], verbose: bool = False):
        self._socket: BroadcastSocket = socket  # Composition over inheritance
        self._manifesto: Dict[str, Dict[str, Any]] = manifesto
        self._channel: int = 0
        self._original_message: Dict[str, Any] = {}
        self._recoverable_message: Dict[str, Any] = {}
        self._active_message = False
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
            if self._active_message:
                message_identity: int = self._recoverable_message[TalkieKey.IDENTITY.value]
                if (self.message_id() - message_identity) & 0xFFFF > 500:
                    self._active_message = False

            received = self._socket.receive()
            if received:
                data, ip_port = received  # Explicitly ignore (ip, port)
                try:
                    if self._verbose:
                        print(data, end="")
                        print(" | from ip: ", end="")
                        print(ip_port, end="")

                    data_array: bytearray = bytearray(data)
                    message_checksum: int = JsonTalkie.get_number(data_array, 'c')
                    JsonTalkie.remove(data_array, 'c')
                    checksum: int = JsonTalkie.generate_checksum(data_array)
                    if message_checksum != checksum:
                        if self._verbose:
                            print(" | FAIL CHECKSUM")
                        pass    # Checksum not validated
                    if self._verbose:
                        print(" | ", end="")
                        print(checksum)
                    message: Dict[str, Any] = JsonTalkie.decode( bytes(data_array) )
                    if self.validate_message(message):

                        match message[TalkieKey.MESSAGE.value]:

                            # Add info to echo message right away accordingly to the message original type
                            case MessageValue.ECHO.value:

                                match JsonTalkie.getMessageData(self._original_message, TalkieKey.MESSAGE):
                                    case MessageValue.PING:
                                        actual_time: int = self.message_id()
                                        out_time_ms: int = message[TalkieKey.TIMESTAMP.value]
                                        delay_ms: int = actual_time - out_time_ms
                                        if delay_ms < 0:    # do overflow as if uint16_t in c++
                                            delay_ms += 0xFFFF + 1  # 2^16
                                        if str(0) not in message:  # Don't change value already set
                                            message[ str(0) ] = delay_ms

                            
                            case MessageValue.ERROR.value:

                                if TalkieKey.ERROR.value not in message:
                                    message[ TalkieKey.ERROR.value ] = ErrorValue.CHECKSUM  # Default value
                                
                                match JsonTalkie.getMessageData(message, TalkieKey.ERROR):
                                    case ErrorValue.CHECKSUM:

                                        original_id: int = self._recoverable_message[TalkieKey.IDENTITY.value]
                                        if self._active_message \
                                            and (TalkieKey.IDENTITY.value not in message or message[TalkieKey.IDENTITY.value] == original_id):

                                                if 'M' in self._recoverable_message:    # Allows 2 sends
                                                    self._active_message = False
                                                self._recoverable_message = {'M' if k == 'm' else k: v for k, v in self._recoverable_message.items()}
                                                self.remoteSend(self._recoverable_message)


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
        message[ TalkieKey.BROADCAST.value ] = BroadcastValue.REMOTE.value
        if message.get( TalkieKey.FROM.value ) is not None:
            if message[TalkieKey.FROM.value] != self._manifesto['talker']['name']:
                message[TalkieKey.TO.value] = message[TalkieKey.FROM.value]
                message[ TalkieKey.FROM.value ] = self._manifesto['talker']['name']
        else:
            message[ TalkieKey.FROM.value ] = self._manifesto['talker']['name']

        if TalkieKey.IDENTITY.value not in message:
            message[ TalkieKey.IDENTITY.value ] = JsonTalkie.message_id()
            if message[TalkieKey.MESSAGE.value] < MessageValue.ECHO.value:
                self._original_message = message.copy() # Shouldn't use the same
            if message[TalkieKey.MESSAGE.value] != MessageValue.NOISE.value:
                self._recoverable_message = message.copy() # Shouldn't use the same
                self._active_message = True

        encoded_message: bytes = json.dumps(message, separators=(',', ':')).encode('utf-8')
        data_array: bytearray = bytearray(encoded_message)
        encoded_message = JsonTalkie.insert_checksum(data_array)

        if self._verbose:
            print(encoded_message)
        # Avoids broadcasting flooding
        sent_result: bool = False
        if TalkieKey.TO.value in message and message[ TalkieKey.TO.value ] in self._devices_address:
            sent_result = self._socket.send( encoded_message, self._devices_address[message[ TalkieKey.TO.value ]] )
            if self._verbose:
                print("--> DIRECT SENDING -->")
        else:
            sent_result = self._socket.send( encoded_message )
            if self._verbose:
                print("--> BROADCAST SENDING -->")
        return sent_result
    

    def hereSend(self, message: Dict[str, Any]) -> bool:
        message[ TalkieKey.BROADCAST.value ] = BroadcastValue.SELF.value
        if TalkieKey.IDENTITY.value not in message: # All messages must have an 'i'
            message[ TalkieKey.IDENTITY.value ] = JsonTalkie.message_id()
            if message[TalkieKey.MESSAGE.value] < MessageValue.ECHO.value:
                self._original_message = message.copy() # Shouldn't use the same
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
        return self.processMessage(message)
    

    def transmitMessage(self, message: Dict[str, Any]) -> bool:
        source_data = BroadcastValue( message.get(TalkieKey.BROADCAST.value, BroadcastValue.REMOTE) )   # get is safer than []
        match source_data:
            case BroadcastValue.SELF:
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
                
                case MessageValue.SYSTEM:
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
        if isinstance(message, dict) and TalkieKey.CHECKSUM.value not in message:
            if TalkieKey.MESSAGE.value not in message:
                return False
            if not isinstance(message[TalkieKey.MESSAGE.value], int):
                return False
            if not (TalkieKey.IDENTITY.value in message):
                return False
            if TalkieKey.TO.value in message:
                if isinstance(message[ TalkieKey.TO.value ], int):
                    if message[ TalkieKey.TO.value ] != self._channel:
                        return False
                elif message[ TalkieKey.TO.value ] != self._manifesto['talker']['name']:
                    return False
        else:
            return False
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


    def insert_checksum(json_payload: bytes) -> bytes:
        payload = bytearray(json_payload)   # Becomes mutable

        checksum = JsonTalkie.generate_checksum(payload)
        JsonTalkie.set_number(payload, 'c', checksum)

        return bytes(payload)   # Back to read-only again






    def get_colon_position(payload: bytes, key: str, colon_position: int = 4) -> int:
        """
        payload: compact JSON as bytes
        key: ASCII value of the key character (e.g. ord('k'))
        colon_position: start index (default 4, same as C++)
        returns: index of ':' or 0 if not found
        """
        json_length = len(payload)
        key_byte: int = ord(key)

        # {"k":x} -> minimum length is 7
        if json_length > 6:
            for i in range(colon_position, json_length):
                if (
                    payload[i] == ord(':') and
                    payload[i - 2] == key_byte and
                    payload[i - 3] == ord('"') and
                    payload[i - 1] == ord('"')
                ):
                    return i

        return 0


    # ValueType equivalent
    class ValueType:
        STRING = 0
        INTEGER = 1
        OTHER = 2


    def get_value_position(payload: bytes, key: str, colon_position: int = 4) -> int:
        colon_position = JsonTalkie.get_colon_position(payload, key, colon_position)
        if colon_position:
            return colon_position + 1  # {"k":x}
        return 0

    def get_key_position(payload: bytes, key: str, colon_position: int = 4) -> int:
        colon_position = JsonTalkie.get_colon_position(payload, key, colon_position)
        if colon_position:
            return colon_position - 2  # {"k":x}
        return 0


    class ValueType(IntEnum):
        STRING = 0
        INTEGER = 1
        OTHER = 2
        VOID = 3


    def get_value_type(payload: bytearray, key: str, colon_position: int = 4) -> ValueType:
        key_byte = ord(key)
        json_i = JsonTalkie.get_value_position(payload, key, colon_position)

        if not json_i:
            return JsonTalkie.ValueType.VOID

        length = len(payload)

        # STRING
        if payload[json_i] == ord('"'):
            json_i += 1
            while json_i < length and payload[json_i] != ord('"'):
                json_i += 1
            if json_i == length:
                return JsonTalkie.ValueType.VOID
            return JsonTalkie.ValueType.STRING

        # INTEGER / OTHER
        while json_i < length and payload[json_i] not in (ord(','), ord('}')):
            if payload[json_i] < ord('0') or payload[json_i] > ord('9'):
                return JsonTalkie.ValueType.OTHER
            json_i += 1

        if json_i == length:
            return JsonTalkie.ValueType.VOID

        return JsonTalkie.ValueType.INTEGER


    def get_field_length(payload: bytes, key: str, colon_position: int = 4) -> int:
        field_length = 0
        json_length = len(payload)

        json_i = JsonTalkie.get_value_position(payload, key, colon_position)
        if json_i:
            field_length = 4  # '"k":'

            value_type = JsonTalkie.get_value_type(payload, key, json_i - 1)

            if value_type == JsonTalkie.ValueType.STRING:
                field_length += 2  # the surrounding quotes
                json_i += 1
                while json_i < json_length and payload[json_i] != ord('"'):
                    field_length += 1
                    json_i += 1

            elif value_type == JsonTalkie.ValueType.INTEGER:
                while (
                    json_i < json_length and
                    ord('0') <= payload[json_i] <= ord('9')
                ):
                    field_length += 1
                    json_i += 1

        return field_length


    def get_number(json_payload: bytes, key: str, colon_position: int = 4) -> int:

        json_length: int = len(json_payload)
        json_number: int = 0
        json_i = JsonTalkie.get_value_position(json_payload, key, colon_position)

        if json_i:
            ZERO = ord('0')
            NINE = ord('9')

            while json_i < json_length and ZERO <= json_payload[json_i] <= NINE:
                json_number = json_number * 10 + (json_payload[json_i] - ZERO)
                json_i += 1

        return json_number


    def remove(json_payload: bytearray, key: str, colon_position: int = 4) -> int:
        
        json_length: int = len(json_payload)
        colon_position = JsonTalkie.get_colon_position(json_payload, key, colon_position)

        if colon_position:
            # All keys occupy 3 chars '"k"' to the left of the colon
            field_position = colon_position - 3

            # Length of '"k":value' (without leading/trailing comma)
            field_length = JsonTalkie.get_field_length(json_payload, key, colon_position)

            # Remove heading comma if present
            if field_position > 0 and json_payload[field_position - 1] == ord(','):
                field_position -= 1
                field_length += 1

            # Otherwise remove trailing comma if present
            elif (field_position + field_length < json_length and
                json_payload[field_position + field_length] == ord(',')):
                field_length += 1

            # Shift payload left
            end = json_length - field_length
            for i in range(field_position, end):
                json_payload[i] = json_payload[i + field_length]

            # Remove the slice from the bytearray
            del json_payload[field_position:field_position + field_length]

            # Update length
            json_length -= field_length

            return json_length  # updated length (truthy)

        return 0  # false / not removed


    def number_of_digits(number: int) -> int:
        length = 1  # 0 has 1 digit
        while number > 9:
            number //= 10  # integer division
            length += 1
        return length


    def set_number(json_payload: bytearray, key: str, number: int, colon_position: int = 4) -> bytearray:
        """
        Sets the JSON key `key` to the given integer `number` in the bytearray payload.
        Automatically inserts the key if it does not exist and handles edge cases like '{}'.
        """
        
        json_length: int = len(json_payload)
        key_byte: int = ord(key)

        # Find the colon position for the key
        colon_position = JsonTalkie.get_colon_position(json_payload, key, colon_position)

        # Remove existing key if present
        if colon_position:
            json_length = JsonTalkie.remove(json_payload, key, colon_position)
            if not json_length:
                return 0  # failed to remove

        # Build the key sequence
        json_key = bytearray(b',\"k\":')
        json_key[2] = key_byte

        # Insert the key before the final '}'
        if json_length > 2:
            insert_pos = json_length - 1
            json_payload[insert_pos:insert_pos] = json_key  # grows payload
        elif json_length == 2:  # Edge case '{}'
            json_key = json_key[1:]  # skip ',' for '{}'
            insert_pos = json_length - 1
            json_payload[insert_pos:insert_pos] = json_key
        else:
            # Something wrong, reset
            json_payload[:] = b'{}'
            return 0

        # Insert the number digits as bytes (ASCII)
        if number:
            digits = bytearray()
            n = number
            while n:
                digits.append(ord('0') + n % 10)
                n //= 10
            digits.reverse()
        else:
            digits = b'0'

        insert_pos = len(json_payload) - 1
        json_payload[insert_pos:insert_pos] = digits  # safe insertion

        return json_payload


    def generate_checksum(json_payload: bytearray) -> int:
        """16-bit XOR checksum over 2-byte chunks"""
        json_length: int = len(json_payload)
        checksum = 0
        for i in range(0, json_length, 2):
            chunk = json_payload[i] << 8
            if i + 1 < json_length:
                chunk |= json_payload[i + 1]
            checksum ^= chunk
        return checksum


    def extract_checksum(json_payload: bytearray) -> tuple[int, int]:
        """
        Extract checksum from the key 'c' and zero out the digits in the payload.
        Returns: (new_json_length, extracted_checksum)
        """
        json_length: int = len(json_payload)
        data_checksum = 0
        at_c = False
        new_index = 4  # Optimized {"c": ...
        i = 4

        while i < json_length:
            char = json_payload[i]
            if char == ord(':'):
                if (
                    json_payload[i - 2] == ord('c') and
                    json_payload[i - 3] == ord('"') and
                    json_payload[i - 1] == ord('"')
                ):
                    at_c = True
            elif at_c:
                if char < ord('0') or char > ord('9'):
                    at_c = False
                elif json_payload[i - 1] == ord(':'):
                    data_checksum = char - ord('0')
                    json_payload[i] = ord('0')
                else:
                    data_checksum = data_checksum * 10 + (char - ord('0'))
                    i += 1
                    continue  # Skip copying the char
            json_payload[new_index] = char
            new_index += 1
            i += 1

        return new_index, data_checksum  # updated length and checksum
    
