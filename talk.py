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
from talkie_codes import JsonKey, SourceData, MessageData, SystemData, EchoData



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
                message_data = MessageData.from_name(words[0])
                if message_data is not None:
                    num_of_keys: int = len(words)
                    message = {
                        JsonKey.MESSAGE.value: message_data.value
                    }
                    if num_of_keys > 1:
                        if (SourceData.from_name(words[1]) == SourceData.HERE):
                            message[ JsonKey.SOURCE.value ] = SourceData.HERE.value
                        else:
                            try:
                                message[ JsonKey.TO.value ] = int(words[1]) # Check if it's a Channel first
                            except ValueError:
                                message[ JsonKey.TO.value ] = words[1]

                    match message_data:

                        case MessageData.RUN | MessageData.GET:
                            if num_of_keys > 2:
                                try:
                                    message[ JsonKey.INDEX.value ] = int(words[2])
                                except ValueError:
                                    message[ JsonKey.NAME.value ] = words[2]
                            else:
                                print(f"\t'{words[0]}' misses arguments!")
                                return

                        case MessageData.SET:
                            if num_of_keys > 3:
                                try:
                                    message[ JsonKey.VALUE.value ] = int(words[3])
                                except ValueError:
                                    print(f"\t'{words[2]}' is not an integer!")
                                    return
                                try:
                                    message[ JsonKey.INDEX.value ] = int(words[2])
                                except ValueError:
                                    message[ JsonKey.NAME.value ] = words[2]
                            else:
                                print(f"\t'{words[0]}' misses arguments!")
                                return

                        case MessageData.LIST:
                            if num_of_keys < 2:
                                print(f"\t'{words[0]}' misses arguments!")
                                return
                            
                        case MessageData.SYS:
                            if num_of_keys > 2:
                                message[ JsonKey.VALUE.value ] = words[2]
                            elif num_of_keys == 2:
                                print(f"\t'{words[0]}' misses arguments!")
                                return
                            else:
                                self._print_sys()
                                return

                        case MessageData.TALK:
                            pass

                        case MessageData.CHANNEL:
                            if num_of_keys > 2:
                                message[ JsonKey.VALUE.value ] = words[2]

                        case MessageData.PING:
                            if num_of_keys > 2:
                                message[ JsonKey.DESCRIPTION.value ] = words[2]

                        case _:
                            self._print_help()
                            return

                elif words[0] == "help":
                    self._print_help()
                    return
 
        json_talkie.transmitMessage(message)


    def _print_help(self):
        """Print help"""
        print("\t[talk [talker]]            Prints all Talkers' 'name' and 'description' (but here).")
        print("\t[ping [talker] [data]]     Returns the duration of the round-trip in milliseconds.")
        print("\t[channel [talker]]         Returns the Talker channel.")
        print("\t[channel <talker> <n>]     Sets the Talker channel.")
        print("\t[list <talker>]            List the entire Talker manifesto.")
        print("\t[run <talker> <name>]      Runs the named function.")
        print("\t[set <talker> <name>]      Sets the named variable.")
        print("\t[get <talker> <name>]      Gets the named variable value.")
        print("\t[message here  ...]        The keyword 'here' applies to self Talker alone.")
        print("\t[sys]                      Prints available options for the Talker system.")
        print("\t[exit]                     Exits the command line (Ctrl+D).")
        print("\t[help]                     Shows the present help.")


    def _print_sys(self):
        """Print system help"""
        print("\t[sys <talker> board]       Prints the board description (OS).")
        print("\t[sys <talker> drops]       Returns the number of drops associated to out of time messages.")
        print("\t[sys <talker> delay]       Returns the maximum delay for dropping the message in milliseconds.")
        print("\t[sys <talker> delay d]     Sets a new delay, where 0 means no delay processed (no drops).")
        print("\t[sys <talker> mute]        Mutes the Talker so that becomes silent.")
        print("\t[sys <talker> unmute]      Unmutes the Talker if it's silent.")
        print("\t[sys <talker> muted]       Prints '1' if the Talker is muted.")
        print("\t[sys <talker> socket]      Prints the socket class name.")
        print("\t[sys <talker> talker]      Prints the Talker class name.")
        print("\t[sys <talker> manifesto]   Prints the manifesto class name.")
        


    def generate_prefix(self, message: Dict[str, Any]) -> str:
        """Generate aligned prefix for messages"""
        parts = []
        if JsonKey.ORIGINAL.value in message and JsonKey.FROM.value in message:
            original_message_code = MessageData(message[JsonKey.ORIGINAL.value])    # VERY IMPORTANT, NEVER FORGET .value !!
            if original_message_code == MessageData.LIST:
                action_name = str(MessageData(message[JsonKey.ACTION.value]))
                parts.append(f"\t[{action_name}")
            else:
                parts.append(f"\t[{str(original_message_code)}")
            parts.append(f" {message[JsonKey.FROM.value]}")
            
            match original_message_code:
                case MessageData.LIST:
                    if JsonKey.INDEX.value in message and JsonKey.NAME.value in message:
                        parts.append(f" {message[JsonKey.INDEX.value]}")
                        parts.append(f"|{message[JsonKey.NAME.value]}")

                case MessageData.SYS:
                    parts.append(f" {str(SystemData(message[JsonKey.SYSTEM.value]))}")

                case _:
                    if JsonKey.INDEX.value in message:
                        parts.append(f" {message[JsonKey.INDEX.value]}")
                    elif JsonKey.NAME.value in message:
                        parts.append(f" {message[JsonKey.NAME.value]}")

            parts.append("]")
        
        return "".join(parts)


    def echo(self, message: Dict[str, Any]) -> bool:
        """Handle echo messages with proper alignment"""
        try:
            prefix = self.generate_prefix(message)
            padded_prefix = prefix.ljust(self.max_prefix_length)
            if JsonKey.ORIGINAL.value in message:
                original_message_code = MessageData(message[JsonKey.ORIGINAL.value])   # VERY IMPORTANT, NEVER FORGET .value !!

                match original_message_code:
                    case MessageData.TALK | MessageData.LIST:
                        print(f"{padded_prefix}\t   {str(message[JsonKey.DESCRIPTION.value])}")
                    case MessageData.SYS:
                        system_code = SystemData(message[JsonKey.SYSTEM.value])
                        match system_code:
                            case SystemData.MUTE | SystemData.UNMUTE:
                                if JsonKey.REPLY.value in message:
                                    print(f"{padded_prefix}\t   {str(EchoData(message[JsonKey.ROGER.value]))}", end="")
                                    print(f"\t   {str(message[JsonKey.REPLY.value])}")
                                else:
                                    print(f"{padded_prefix}\t   {str(EchoData(message[JsonKey.ROGER.value]))}")
                        
                            case SystemData.BOARD:
                                print(f"{padded_prefix}\t   {str(message[JsonKey.DESCRIPTION.value])}")

                            case _:
                                print(f"{padded_prefix}\t   {str(message[JsonKey.VALUE.value])}")
                    case _:
                        if JsonKey.VALUE.value in message:
                            if JsonKey.REPLY.value in message:
                                print(f"{padded_prefix}\t   {str(message[JsonKey.VALUE.value])}", end="")
                                print(f"\t   {str(message[JsonKey.REPLY.value])}")
                            else:
                                print(f"{padded_prefix}\t   {str(message[JsonKey.VALUE.value])}")
                        elif JsonKey.ROGER.value in message:
                            if JsonKey.REPLY.value in message:
                                print(f"{padded_prefix}\t   {str(EchoData(message[JsonKey.ROGER.value]))}", end="")
                                print(f"\t   {str(message[JsonKey.REPLY.value])}")
                            else:
                                print(f"{padded_prefix}\t   {str(EchoData(message[JsonKey.ROGER.value]))}")
                        elif JsonKey.DESCRIPTION.value in message:
                            print(f"{padded_prefix}\t   {message[JsonKey.DESCRIPTION.value]}")
                        elif JsonKey.REPLY.value in message:
                            print(f"{padded_prefix}\t   {str(message[JsonKey.REPLY.value])}")

            return True
        except Exception as e:
            print(f"\nFormat error: {e}")
            return False



    def error(self, message: Dict[str, Any]) -> bool:
        """Handle error messages"""
        if JsonKey.FROM.value in message:
            print(f"\t[{message['f']}", end='')
            if JsonKey.ERROR.value in message and isinstance(message[ JsonKey.ERROR.value ], int):
                error_messages = {
                    0: "Message NOT for me",
                    1: "Unknown sender",
                    2: "Message corrupted",
                    3: "Wrong message code",
                    4: "Message NOT identified",
                    5: "Set command arrived too late"
                }
                print(f"]\tERROR\t{error_messages.get(message['e'], 'Unknown')}")
            else:
                print("]\tUnknown error")
        return True

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
        "--verbose",
        action="store_true",
        default=False,
        help="Enables verbose mode"
    )
    
    args = parser.parse_args()
    
    # Socket configuration from command line
    SOCKET: str = args.socket
    VERBOSE: bool = args.verbose
    
    if SOCKET == "SERIAL":
        from broadcast_socket_serial import BroadcastSocket_Serial
        broadcast_socket = BroadcastSocket_Serial("COM4")
    elif SOCKET == "DUMMY":
        from broadcast_socket_dummy import BroadcastSocket_Dummy
        broadcast_socket = BroadcastSocket_Dummy()
    else:
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



