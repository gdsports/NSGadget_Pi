# NS Gadget Voice Assistant

The Raspberry Pi 4 is fast enough to do speech-to-text (STT) also known
as voice recognition without help from the Internet. A simple demo of this
has been integrated in nsac.py. Gamepads and joysticks may be used at the
same time as the voice assistant.

The STT engine is the Mozilla DeepSpeech engine. This can also run on a
Pi 3+ but the Pi 4 is about twice as fast.

For this project, DeepSpeech runs as a separate process writing text one
line at a time to standard output. The text is piped to standard input of
nsac.py. The read_speech function matches each line against a dictionary
of words and phrases. If a match is found, nsac.py outputs the corresponding
NS gamepad buttons presses and releases. More than one button may be pressed
at the same time.

## Install Mozilla DeepSpeech

Follow this [guide](https://github.com/touchgadget/DeepSpeech).

## Files

### dspeech

Shell script to start the DeepSpeech engine running. See dspeech_mic.py

### dspeech_mic.py

Python3 program that reads from a microphone and writes lines of text to
standard output.

### nsac_voice.sh

Run Deep Speech and nsac.py connected by a pipe.

```
./nsac_voice.sh
```

## Some thoughts on the code

The read_speech function in nsac.py reads one line at a time from standard
input then looks up the line of text in a Python dictionary. If a match is
found, the corresponding buttons are pressed and released. Only part of the
command dictionary included because it is very long.


```python
    COMMAND_DICT = {
            ...

            'whistle': {'dpad': NSDPad.DOWN},
            'call horse': {'dpad': NSDPad.DOWN},
            'called horse': {'dpad': NSDPad.DOWN},
            'all horse': {'dpad': NSDPad.DOWN},
            'horse': {'dpad': NSDPad.DOWN},
            'a horse': {'dpad': NSDPad.DOWN},
            'get horse': {'dpad': NSDPad.DOWN},
            'get a horse': {'dpad': NSDPad.DOWN},

            ...
    }
    for line in sys.stdin:
    command = line.rstrip()
    print(command)
    if command in COMMAND_DICT:
        controls = COMMAND_DICT[command]
        print(controls)
        if 'buttons' in controls:
            for btn in controls['buttons']:
                print('press ', btn)
                NSG.press(btn)
        if 'dpad' in controls:
            print('dpad ', controls['dpad'])
            NSG.dPad(controls['dpad'])
        time.sleep(0.075)
        if 'dpad' in controls:
            print('dpad centered')
            NSG.dPad(NSDPad.CENTERED)
        if 'buttons' in controls:
            for btn in reversed(controls['buttons']):
                print('release ', btn)
                NSG.release(btn)
```

For "Zelda: Breath Of The Wild", pressing the direction pad down arrow makes
the character Link whistle for a horse. The dictionary has many synonyms for
whistle because Deep Speech has great difficulty with the word. The problem
could just be my voice. I added the two phrases "call horse" and "get horse".
Then I added all the mistakes that Deep Speech frequently returns.
