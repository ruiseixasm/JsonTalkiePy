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
import os
import uuid
import asyncio
import argparse
from typing import Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from json_talkie import JsonTalkie
from talkie_codes import TalkieKey, BroadcastValue, MessageValue, SystemValue, RogerValue, ErrorValue



class CommandLine:
    def __init__(self):
        self.manifesto: Dict[str, Dict[str, Any]] = {
            'talker': {
                'name': f"Talker-{str(uuid.uuid4())[:2]}",
                'description': 'A simple Talker!'
            },
            'echo': self.echo,
            'error': self.error
        }

        # Ensure history file exists
        if not os.path.exists(".cmd_history"):
            open(".cmd_history", 'w').close()

        try:
            self.session = PromptSession(history=FileHistory('.cmd_history'))
        except Exception:
            self.session = None

        self.max_prefix_length = 22  # Fixed alignment width


    async def run(self):
        """Async version of the main loop"""
        while True:
            try:
                with patch_stdout():
                    cmd = await self.session.prompt_async(">>> ")
                if not cmd:
                    continue
                
                await self._execute(cmd)
                
            except EOFError:  # Ctrl+D
                print("\tExiting...")
                break
            except KeyboardInterrupt:  # Ctrl+C
                print("\tUse Ctrl+D to exit")
                continue
            except Exception as e:
                print(f"\tError: {e}")


    async def _execute(self, cmd: str):
        """Async command execution handler"""
        cmd = cmd.strip()
        if cmd in ("exit", "quit"):
            raise EOFError
        elif cmd == "history":
            with open('.cmd_history', 'r') as f:
                for i, line in enumerate(f, 1):
                    print(f"{i}: {line.strip()}")
        else:
            words = cmd.split()
            if words:
                message_data = MessageValue.from_name(words[0])
                if message_data is not None:
                    num_of_keys: int = len(words)
                    message = {
                        TalkieKey.MESSAGE.value: message_data.value
                    }
                    if num_of_keys > 1:
                        if (BroadcastValue.from_name(words[1]) == BroadcastValue.SELF):
                            message[ TalkieKey.BROADCAST.value ] = BroadcastValue.SELF.value
                        else:
                            try:
                                message[ TalkieKey.TO.value ] = int(words[1]) # Check if it's a Channel first
                            except ValueError:
                                message[ TalkieKey.TO.value ] = words[1]

                    match message_data:

                        case MessageValue.CALL:
                            if num_of_keys > 2:
                                # Action index or name
                                try:
                                    message[ TalkieKey.ACTION.value ] = int(words[2])
                                except ValueError:
                                    message[ TalkieKey.ACTION.value ] = words[2]
                                message_keys: int = 3
                                if num_of_keys > message_keys:  # Extra values
                                    for value_i in range(num_of_keys - message_keys):
                                        value_word: str = words[message_keys + value_i]
                                        try:
                                            message[ str(value_i) ] = int(value_word)
                                        except ValueError:
                                            message[ str(value_i) ] = value_word
                            else:
                                print(f"\t'{words[0]}' misses arguments!")
                                return

                        case MessageValue.LIST:
                            if num_of_keys < 2:
                                print(f"\t'{words[0]}' misses arguments!")
                                return
                            
                        case MessageValue.SYSTEM:
                            if num_of_keys > 2:
                                if SystemValue.from_name(words[2]) is not None:
                                    message[ TalkieKey.SYSTEM.value ] = SystemValue.from_name(words[2]).value
                                else:
                                    print(f"\t'{words[2]}' isn't a valid SystemData code!")
                                    return
                                message_keys: int = 3
                                if num_of_keys > message_keys:  # Extra values
                                    for value_i in range(num_of_keys - message_keys):
                                        value_word: str = words[message_keys + value_i]
                                        try:
                                            message[ str(value_i) ] = int(value_word)
                                        except ValueError:
                                            message[ str(value_i) ] = value_word
                            elif num_of_keys == 2:
                                print(f"\t'{words[0]}' misses arguments!")
                                return
                            else:
                                self._print_info()
                                return

                        case MessageValue.TALK:
                            pass

                        case MessageValue.CHANNEL:
                            message_keys: int = 2
                            if num_of_keys > message_keys:  # Extra values
                                for value_i in range(num_of_keys - message_keys):
                                    value_word: str = words[message_keys + value_i]
                                    try:
                                        message[ str(value_i) ] = int(value_word)
                                    except ValueError:
                                        message[ str(value_i) ] = value_word

                        case MessageValue.PING:
                            message_keys: int = 2
                            if num_of_keys > message_keys:  # Extra values
                                for value_i in range(num_of_keys - message_keys):
                                    value_word: str = words[message_keys + value_i]
                                    try:
                                        message[ str(value_i) ] = int(value_word)
                                    except ValueError:
                                        message[ str(value_i) ] = value_word

                        case _:
                            self._print_help()
                            return

                else:
                    self._print_help()
                    return
 
        json_talkie.transmitMessage(message)


    def _print_help(self):
        """Generic help"""
        print("\t[talk [talker]]            Prints all Talkers' 'name' and 'description' (but here).")
        print("\t[ping [talker] [data]]     Returns the duration of the round-trip in milliseconds.")
        print("\t[channel [talker]]         Returns the Talker channel.")
        print("\t[channel <talker> <n>]     Sets the Talker channel.")
        print("\t[list <talker>]            List the entire Talker manifesto.")
        print("\t[call <talker> <name>]     Calls a named action.")
        print("\t[message here  ...]        The keyword 'here' applies to self Talker alone.")
        print("\t[system]                   Prints available options for the Talker system.")
        print("\t[exit]                     Exits the command line (Ctrl+D).")
        print("\t[help]                     Shows the present help.")


    def _print_info(self):
        """System help:"""
        print("\t[system <talker> board]    Prints the board description (OS).")
        print("\t[system <talker> mute]     Gets or sets the Talker Calls muted state, 1 for silent and 0 for not.")
        print("\t[system <talker> errors]   Returns the number of errors per socket, bad checksum transfers.")
        print("\t[system <talker> drops]    Returns the number of drops associated to out of time messages.")
        print("\t[system <talker> delay]    Returns the maximum delay for dropping the message in milliseconds.")
        print("\t[system <talker> delay d]  Sets a new delay, where 0 means no delay processed (no drops).")
        print("\t[system <talker> sockets]  Prints all connected sockets to the talker.")
        print("\t[system <talker> manifesto]Prints the manifesto class name.")
        


    def generate_prefix(self, message: Dict[str, Any]) -> str:
        """Generate aligned prefix for messages"""
        parts = []

        if TalkieKey.FROM.value in message:
            from_talker = message[TalkieKey.FROM.value]
        elif TalkieKey.BROADCAST.value in message and message[TalkieKey.BROADCAST.value] == BroadcastValue.SELF.value:
            from_talker = json_talkie._manifesto['talker']['name']
        else:
            return ""

        original_message = json_talkie._original_message
        original_message_data = original_message.get( TalkieKey.MESSAGE.value )
        if original_message_data == MessageValue.LIST:
            parts.append(f"\t[{str(MessageValue.CALL)}")
        else:
            parts.append(f"\t[{str(MessageValue( original_message_data ))}")
        parts.append(f" {from_talker}")
        
        match original_message_data:
            case MessageValue.LIST:
                if str(0) in message and str(1) in message:
                    parts.append(f" {message[ str(0) ]}")
                    parts.append(f"|{message[ str(1) ]}")

            case MessageValue.SYSTEM:
                parts.append(f" {str(SystemValue(message[TalkieKey.SYSTEM.value]))}")

            case _:
                if TalkieKey.ACTION.value in original_message:
                    parts.append(f" {original_message[TalkieKey.ACTION.value]}")
                elif TalkieKey.ACTION.value in original_message:
                    parts.append(f" {original_message[TalkieKey.ACTION.value]}")

        parts.append("]")
        
        return "".join(parts)


    @staticmethod
    def print_message_data(message: Dict[str, Any], start_at: int = 0):
        value_i: int = start_at
        while(str(value_i) in message):
            print(f"\t   {str(message[ str(value_i) ])}", end="")
            value_i += 1
        print() # Adds the final new line


    def echo(self, message: Dict[str, Any]) -> bool:
        """Handle echo messages with proper alignment"""
        try:
            prefix = self.generate_prefix(message)
            padded_prefix = prefix.ljust(self.max_prefix_length)

            original_message_data = json_talkie._original_message.get( TalkieKey.MESSAGE.value )
            match original_message_data:
                case MessageValue.TALK:
                    print(f"{padded_prefix}", end="")
                    self.print_message_data(message)
                case MessageValue.LIST:
                    print(f"{padded_prefix}", end="")
                    if TalkieKey.ROGER.value in message:
                        print(f"\t   {RogerValue(message[TalkieKey.ROGER.value])}", end="")
                        self.print_message_data(message, 0)
                    else:
                        self.print_message_data(message, 2)
                case MessageValue.CALL:
                    print(f"{padded_prefix}", end="")
                    if TalkieKey.ROGER.value not in message:
                        print(f"\t   {str(RogerValue.ROGER)}", end="")
                    else:
                        print(f"\t   {RogerValue(message[TalkieKey.ROGER.value])}", end="")
                    self.print_message_data(message)
                case _:
                    print(f"{padded_prefix}", end="")
                    if TalkieKey.ROGER.value in message:
                        print(f"\t   {RogerValue(message[TalkieKey.ROGER.value])}", end="")
                    self.print_message_data(message)

            return True
        except Exception as e:
            print(f"\nFormat error: {e}")
            return False



    def error(self, message: Dict[str, Any]) -> bool:
        """Handle echo messages with proper alignment"""
        try:
            prefix = self.generate_prefix(message)
            padded_prefix = prefix.ljust(self.max_prefix_length)

            print(f"{padded_prefix}", end="")
            print(f"\t   {MessageValue(message[TalkieKey.MESSAGE.value])}", end="")
            print(f"\t   {ErrorValue(message[TalkieKey.ERROR.value])}", end="")
            self.print_message_data(message)

            return True
        except Exception as e:
            print(f"\nFormat error: {e}")
            return False


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="JSON Talkie Communication Tool")
    parser.add_argument(
        "--socket", 
        choices=["UDP", "SERIAL", "DUMMY"], 
        default="UDP",
        help="Socket type to use (default: UDP)"
    )
    parser.add_argument(
        "--port",
        default="COM5",
        help="Serial port to use when socket type is SERIAL (default: COM5)"
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Baud rate for serial communication (default: 115200)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enables verbose mode"
    )
    
    args = parser.parse_args()
    
    # Socket configuration from command line
    SOCKET: str = args.socket
    SERIAL_PORT: str = args.port
    SERIAL_BAUD: int = args.baud
    VERBOSE: bool = args.verbose
    
    # Create appropriate socket instance
    if SOCKET == "SERIAL":
        from broadcast_socket_serial import BroadcastSocket_Serial
        broadcast_socket = BroadcastSocket_Serial(SERIAL_PORT, SERIAL_BAUD)
    elif SOCKET == "DUMMY":
        from broadcast_socket_dummy import BroadcastSocket_Dummy
        broadcast_socket = BroadcastSocket_Dummy()
    else:  # UDP
        from broadcast_socket_udp import BroadcastSocket_UDP
        broadcast_socket = BroadcastSocket_UDP()

    cli = CommandLine()
    json_talkie = JsonTalkie(broadcast_socket, cli.manifesto, VERBOSE)

    if not json_talkie.on():
        print("\tFailed to turn jsonTalkie On!")
        exit(1)
    
    print(f"\tWARNINGS TO AVOID UNREACHABLE MESSAGES:")
    print(f"\t\tALWAYS GIVE DIFFERENT MAC ADDRESSES TO YOUR DEVICES DUE TO IP CONFLICTS")
    print(f"\t\tAVOID BROADCASTED MESSAGES ON WIFI CONNECTED DEVICES DUE TO WIFI RESTRICTIONS")
    print(f"\t[{cli.manifesto['talker']['name']}] running. Type 'exit' to exit or 'talk' to make them talk.")
    
    try:
        asyncio.run(cli.run())
    finally:
        json_talkie.off()


