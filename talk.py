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
                if words[0] == "port":
                    if len(words) == 2:
                        try:
                            broadcast_socket.set_port(int(words[1]))
                        except ValueError:
                            print(f"\t'{words[1]}' is not an integer!")
                    actual_port: int = broadcast_socket.get_port()
                    print(f"\t[port]               \t{actual_port}")
                    return
                elif len(words) == 1:
                    if words[0] == "talk":
                        message = {"m": 0}
                        json_talkie.talk(message)
                        return
                    elif words[0] == "sys":
                        message = {"m": 5}
                        json_talkie.talk(message)
                        return
                else:
                    message: dict = {}
                    try:    # Try as channel first
                        message["t"] = int(words[0])
                    except ValueError:
                        if words[0] != "*":
                            message["t"] = words[0]
                    command_map = {
                        "talk": (0, 2),
                        "list": (1, 2),
                        "run": (2, 3),
                        "set": (3, 4),
                        "get": (4, 3),
                        "sys": (5, 2),
                        "channel": (8, 0)
                    }
                    
                    if words[1] in command_map:
                        code, total_args = command_map[words[1]]
                        if len(words) == total_args or total_args == 0:
                            message["m"] = code
                            if code == 8:   # channel
                                if len(words) == 3:
                                    try:
                                        message["b"] = int(words[2])
                                    except ValueError:
                                        print(f"\t'{words[2]}' is not an integer!")
                                        return
                            elif total_args > 2:
                                try:    # Try as number first
                                    message["N"] = int(words[2])
                                except ValueError:
                                    message["n"] = words[2]
                            if words[1] == "set":
                                try:
                                    message["v"] = int(words[3])
                                except ValueError:
                                    print(f"\t'{words[3]}' is not an integer!")
                                    return
                            json_talkie.talk(message)
                            return
                        else:
                            print(f"\t'{words[1]}' requires {total_args - 2} argument(s)!")
                            return
                        
        self._print_help()

    def _print_help(self):
        """Print command help"""
        print("\t[talk]               \tPrints all devices' 'name' and description.")
        print("\t['device' list]      \tList the entire 'device' manifesto.")
        print("\t['device' channel]   \tShows the Device channel.")
        print("\t['device' channel n] \tSets the Device channel.")
        print("\t['device' run 'what']\tRuns the named function.")
        print("\t['device' set 'what']\tSets the named variable.")
        print("\t['device' get 'what']\tGets the named variable value.")
        print("\t[sys]                \tPrints the platform of the Device.")
        print("\t[port]               \tGets the Broadcast Socket port.")
        print("\t[port n]             \tSets the Broadcast Socket port.")
        print("\t[exit]               \tExits the command line (Ctrl+D).")
        print("\t[help]               \tShows the present help.")


    def generate_prefix(self, message: Dict[str, Any]) -> str:
        """Generate aligned prefix for messages"""
        parts = []
        if "f" in message:
            parts.append(f"\t[{message['f']}")
            
            if "w" in message:
                what = {
                    0: "talk", 1: "list", 2: "run",
                    3: "set", 4: "get", 5: "sys", 8: "channel"
                }.get(message.get("w"), "echo")
                parts.append(f" {what}")
                
                if "N" in message:
                    parts.append(f" {message['N']}")
                    if "n" in message:
                        parts.append(f"|{message['n']}")
                elif "n" in message:
                    parts.append(f" {message['n']}")
            
            parts.append("]")
        
        return "".join(parts)


    def echo(self, message: Dict[str, Any]) -> bool:
        """Handle echo messages with proper alignment"""
        try:
            prefix = self.generate_prefix(message)
            padded_prefix = prefix.ljust(self.max_prefix_length)
            
            echo_reply: dict = {}

            if "w" in message:
                echo_reply[0] = {
                    0: "talk", 1: "list", 2: "run",
                    3: "set", 4: "get", 5: "sys", 8: "channel"
                }.get(message.get("w"), "echo")

            if "g" in message:
                echo_reply[1] = {
                    0: "ROGER", 1: "SAY AGAIN", 2: "NEGATIVE"
                }.get(message["g"], "FAIL")
            elif "v" in message:
                echo_reply[2] = str(message["v"])
            elif "b" in message:
                echo_reply[1] = str(message["b"])
            elif "d" in message:
                echo_reply[1] = str(message["d"])
            
            if 1 in echo_reply:
                print(f"{padded_prefix}\t{echo_reply[1]}")
            if 2 in echo_reply:
                print(f"{padded_prefix}\t{echo_reply[2]}")

            # If it carries a reply
            if "r" in message:	
                print(f"{padded_prefix}\t{str(message["r"])}")

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

    from json_talkie import JsonTalkie
    
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



