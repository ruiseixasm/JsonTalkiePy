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
from talkie_codes import JsonChar, MessageData, SystemData, EchoData



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
                if len(words) == 1:
                    if words[0] == str(MessageData.TALK):
                        message = {"m": MessageData.TALK.value}
                        json_talkie.talk(message)
                        return
                    elif words[0] == str(MessageData.SYS):
                        self._print_sys()
                        return
                else:   # WITH TARGET NAME DEFINED
                    message: dict = {}
                    try:    # Try as channel first
                        message["t"] = int(words[0])
                    except ValueError:
                        if words[0] != "*":
                            message["t"] = words[0]

                    if MessageData.validate_to_words(words):
                        message["m"] = MessageData.from_name(words[1]).value
                        match MessageData.from_name(words[1]):
                            case MessageData.RUN | MessageData.GET:
                                try:    # Try as number first
                                    message["x"] = int(words[2])
                                except ValueError:
                                    message["n"] = words[2]
                            case MessageData.SET:
                                try:    # Try as number first
                                    message["x"] = int(words[2])
                                except ValueError:
                                    message["n"] = words[2]
                                try:
                                    message["v"] = int(words[3])
                                except ValueError:
                                    print(f"\t'{words[3]}' is not an integer!")
                                    return
                            case MessageData.CHANNEL:
                                if len(words) > 2:
                                    try:
                                        message["b"] = int(words[2])
                                    except ValueError:
                                        print(f"\t'{words[2]}' is not an integer!")
                                        return
                            case MessageData.SYS:
                                if len(words) > 2:
                                    if (SystemData.from_name(words[2])):
                                        message["s"] = SystemData.from_name(words[2]).value
                                    else:
                                        self._print_sys()
                                        return
                                else:
                                    self._print_sys()
                                    return
                                if len(words) > 3:
                                    try:    # Try as number first
                                        message["v"] = int(words[3])
                                    except ValueError:
                                        message["v"] = words[3]
                            case _:
                                self._print_help()
                                return
                                    
                        json_talkie.talk(message)
                        return
                        
        self._print_help()


    def _print_help(self):
        """Print help"""
        print("\t[talk]                     Prints all talkers' 'name' and 'description'.")
        print("\t['talker' list]            List the entire 'talker' manifesto.")
        print("\t['talker' channel]         Returns the Device channel.")
        print("\t['talker' channel n]       Sets the Device channel.")
        print("\t['talker' run 'name']      Runs the named function.")
        print("\t['talker' set 'name']      Sets the named variable.")
        print("\t['talker' get 'name']      Gets the named variable value.")
        print("\t[sys]                      Prints available options for the 'talker' system.")
        print("\t[* 'action' '...']         The wildcard '*' means all talkers.")
        print("\t[exit]                     Exits the command line (Ctrl+D).")
        print("\t[help]                     Shows the present help.")


    def _print_sys(self):
        """Print system help"""
        print("\t['talker' sys board]       Prints the board description (OS).")
        print("\t['talker' sys ping]        Returns the duration of the round-trip in milliseconds.")
        print("\t['talker' sys ping d]      Sets some overloading data to a more realistic measurement.")
        print("\t['talker' sys drops]       Returns the number of drops associated to out of time messages.")
        print("\t['talker' sys delay]       Returns the maximum delay for dropping the message in milliseconds.")
        print("\t['talker' sys delay d]     Sets a new delay, where 0 means no delay processed (no drops).")
        print("\t['talker' sys mute]        Mutes the talker so that becomes silent.")
        print("\t['talker' sys unmute]      Unmutes the talker if it's silent.")
        print("\t['talker' sys muted]       Prints '1' if the talker is muted.")
        print("\t['talker' sys socket]      Prints the socket class name.")
        print("\t['talker' sys talker]      Prints the talker class name.")
        print("\t['talker' sys manifesto]   Prints the manifesto class name.")
        


    def generate_prefix(self, message: Dict[str, Any]) -> str:
        """Generate aligned prefix for messages"""
        parts = []
        if JsonChar.FROM.value in message:
            parts.append(f"\t[{message[JsonChar.FROM.value]}")  # VERY IMPORTANT, NEVER FORGET .value !!
            
            if JsonChar.ORIGINAL.value in message:
                original_message_code = MessageData(message[JsonChar.ORIGINAL.value])
                match original_message_code:
                    case MessageData.LIST:
                        action_name = str(MessageData(message[JsonChar.ACTION.value]))
                        parts.append(f" {action_name}")
                        if JsonChar.INDEX.value in message and JsonChar.NAME.value in message:
                            parts.append(f" {message[JsonChar.INDEX.value]}")
                            parts.append(f"|{message[JsonChar.NAME.value]}")

                    case MessageData.SYS:
                        parts.append(f" {str(original_message_code)}")
                        parts.append(f" {str(SystemData(message[JsonChar.SYSTEM.value]))}")

                    case _:
                        parts.append(f" {str(original_message_code)}")
                        if JsonChar.INDEX.value in message:
                            parts.append(f" {message[JsonChar.INDEX.value]}")
                        elif JsonChar.NAME.value in message:
                            parts.append(f" {message[JsonChar.NAME.value]}")


            parts.append("]")
        
        return "".join(parts)


    def echo(self, message: Dict[str, Any]) -> bool:
        """Handle echo messages with proper alignment"""
        try:
            prefix = self.generate_prefix(message)
            padded_prefix = prefix.ljust(self.max_prefix_length)
            if JsonChar.ORIGINAL.value in message:
                original_message_code = MessageData(message[JsonChar.ORIGINAL.value])   # VERY IMPORTANT, NEVER FORGET .value !!

                match original_message_code:
                    case MessageData.TALK | MessageData.LIST:
                        print(f"{padded_prefix}\t{str(message[JsonChar.DESCRIPTION.value])}")
                    case MessageData.SYS:
                        system_code = SystemData(message[JsonChar.SYSTEM.value])
                        match system_code:
                            case SystemData.MUTE | SystemData.UNMUTE:
                                print(f"{padded_prefix}\t{str(EchoData(message[JsonChar.ROGER.value]))}")
                                if JsonChar.REPLY.value in message:
                                    print(f"{padded_prefix}\t{str(message[JsonChar.REPLY.value])}")
                        
                            case SystemData.BOARD:
                                print(f"{padded_prefix}\t{str(message[JsonChar.DESCRIPTION.value])}")

                            case SystemData.PING:
                                if "delay_ms" in message:
                                    print(f"{padded_prefix}\t{str(message["delay_ms"])}")
                                else:
                                    print(f"{padded_prefix}\t{"unknown"}")

                            case _:
                                print(f"{padded_prefix}\t{str(message[JsonChar.VALUE.value])}")
                    case _:
                        if JsonChar.VALUE.value in message:
                            print(f"{padded_prefix}\t{str(message[JsonChar.VALUE.value])}")
                        elif JsonChar.ROGER.value in message:
                            print(f"{padded_prefix}\t{str(EchoData(message[JsonChar.ROGER.value]))}")
                        else:
                            print(f"{padded_prefix}\t{message[JsonChar.DESCRIPTION.value]}")
                        if JsonChar.REPLY.value in message:
                            print(f"{padded_prefix}\t{str(message[JsonChar.REPLY.value])}")

            # Remove the exceeding messages from the pool


            return True
        except Exception as e:
            print(f"\nFormat error: {e}")
            return False



    def error(self, message: Dict[str, Any]) -> bool:
        """Handle error messages"""
        if "f" in message:
            print(f"\t[{message['f']}", end='')
            if "e" in message and isinstance(message["e"], int):
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
    
    print(f"\tWARNINGS TO AVOID UNREACHABLE COMMANDS:")
    print(f"\t\tALWAYS GIVE DIFFERENT MAC ADDRESSES TO YOUR DEVICES DUE TO IP CONFLICTS")
    print(f"\t\tAVOID BROADCASTED (UNNAMED DEVICES) COMMANDS ON WIFI CONNECTED DEVICES DUE TO WIFI RESTRICTIONS")
    print(f"\t[{cli.manifesto['talker']['name']}] running. Type 'exit' to exit or 'talk' to make them talk.")
    
    try:
        asyncio.run(cli.run())
    finally:
        json_talkie.off()



