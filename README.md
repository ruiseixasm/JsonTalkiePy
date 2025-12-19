# JsonTalkie - JSON-based Communication for Arduino

A lightweight library for Arduino communication and control using JSON messages over network sockets, with Python companion scripts for host computer interaction.

## Features

- Bi-directional JSON-based communication between Arduino and Python
- Simple command/response pattern with "Walkie-talkie" style interaction
- Device configuration with a Manifesto for self-describing capabilities
- Automatic command discovery and documentation
- Support for multiple devices on the same network

## Installation
   - Go to a folder in your system and type `git clone https://github.com/ruiseixasm/JsonTalkiePy.git`
   - Go to the newly created `JsonTalkiePy` folder and type `python talk.py`

## JsonTalkie Arduino Library
   - To be used with the Arduino [JsonTalkie](https://github.com/ruiseixasm/JsonTalkie) library (version 3.0 or above)
   - Go to the site above for instructions in how to install it

## Python Command Line
### Typical usage
```bash
rui@acer:~/GitHub/JsonTalkie/Python$ python3.13 talk.py 
	[Talker-1b] running. Type 'exit' to exit or 'talk' to make them talk.
>>> talk
	[Talker-1b talk]     	A simple Talker!
	[Nano talk]          	I do a 500ms buzz!
>>> Nano info
	[Nano info]            	Arduino Uno/Nano (ATmega328P)
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
	[info]                   Prints the platform of the Device.
	[port]                  Gets the Broadcast Socket port.
	[port n]                Sets the Broadcast Socket port.
	[exit]                  Exits the command line (Ctrl+D).
	[help]                  Shows the present help.
>>> exit
	Exiting...
```
### Channel setting
In order to command multiple devices at once, instead of calling them by name you can call them by `channel`.
This applies to all commands besides the `talk` one used bellow by `channel`.
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
