# JsonTalkie - JSON-based Communication for Arduino

A lightweight library for Arduino communication and control using JSON messages over network sockets, with Python companion scripts for host computer interaction.

## Features

- Bi-directional JSON-based communication between Arduino and Python
- Simple command/response pattern with "Walkie-talkie" style interaction
- Device configuration with a Manifesto for self-describing capabilities
- Automatic command discovery and documentation
- Support for multiple devices on the same network

## Installation

### Arduino Library
1. **Using Arduino Library Manager**:
   - Open Arduino IDE
   - Go to `Sketch > Include Library > Manage Libraries`
   - Search for "JsonTalkie"
   - Click "Install"

2. **Manual Installation**:
   - Download the latest release from GitHub
   - Extract to your Arduino libraries folder
   - Restart Arduino IDE

### JsonTalkie
   - To be used in conjugation with the Arduino [JsonTalkie](https://github.com/ruiseixasm/JsonTalkie) library (version 3.0 or above)

## Python Command Line
### Typical usage
```bash
rui@acer:~/GitHub/JsonTalkie/Python$ python3.13 talk.py 
	[Talker-1b] running. Type 'exit' to exit or 'talk' to make them talk.
>>> talk
	[Talker-1b talk]     	A simple Talker!
	[Nano talk]          	I do a 500ms buzz!
>>> Nano sys
	[Nano sys]            	Arduino Uno/Nano (ATmega328P)
>>> Nano list
	[Nano run buzz]      	Triggers buzzing
	[Nano run on]        	Turns led On
	[Nano run off]       	Turns led Off
	[Nano get total_runs]	Gets the total number of runs
>>> Nano run buzz
	[Nano run buzz]      	ROGER
>>> help
	[talk]                  Prints all devices' 'name' and description.
	['device' list]         List the entire 'device' manifesto.
	['device' channel]      Shows the Device channel.
	['device' channel n]    Sets the Device channel.
	['device' run 'what']   Runs the named function.
	['device' set 'what']   Sets the named variable.
	['device' get 'what']   Gets the named variable value.
	[sys]                   Prints the platform of the Device.
	[port]                  Gets the Broadcast Socket port.
	[port n]                Sets the Broadcast Socket port.
	[exit]                  Exits the command line (Ctrl+D).
	[help]                  Shows the present help.
>>> exit
	Exiting...
```
### Channel setting
In order to command multiple devices at once, instead of calling them by name call them by `channel`.
```bash
PS C:\Users\Utilizador\Documents\GitHub\JsonTalkiePy> python .\talk.py
        [Talker-ae] running. Type 'exit' to exit or 'talk' to make them talk.
>>> talk
        [Talker-ae talk]        A simple Talker!
        [Nano talk]             I do a 500ms buzz!
        [ESP32 talk]            I do a 500ms buzz!
        [ESP66 talk]            I do a 500ms buzz!
>>> * channel
        [Talker-ae channel]     0
        [Nano channel]          0
        [ESP32 channel]         0
        [ESP66 channel]         0
>>> Nano channel 11
        [Nano channel]          11
>>> ESP66 channel 11
        [ESP66 channel]         11
>>> 0 talk
        [Talker-ae talk]        A simple Talker!
        [ESP32 talk]            I do a 500ms buzz!
>>> 11 talk
        [Nano talk]             I do a 500ms buzz!
        [ESP66 talk]            I do a 500ms buzz!
>>> * channel
        [Talker-ae channel]     0
        [Nano channel]          11
        [ESP32 channel]         0
        [ESP66 channel]         11
>>> exit
        Exiting...
PS C:\Users\Utilizador\Documents\GitHub\JsonTalkiePy>
```
