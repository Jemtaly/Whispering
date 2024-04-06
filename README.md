# Whispering
A real-time transcription and translation tool implemented in Python based on the [fast-whisper](https://github.com/SYSTRAN/faster-whisper) library.

## Requirements

- Python 3.8+
- [fast-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition)
- [PyAudio](https://pypi.org/project/PyAudio) 0.2.11+

## Usage

```
usage: whispering.py [-h] [--size {tiny,base,small,medium,large}] [--device DEVICE]
                     [--latency LATENCY] [--patience PATIENCE] [--flush] [--amnesia]
                     [--prompt PROMPT] [--deliberation {1,2,3}] [--source SOURCE]
                     [--target TARGET] [--tui]

Transcribe and translate speech in real-time.

options:
  -h, --help            show this help message and exit
  --size {tiny,base,small,medium,large}
                        size of the model to use
  --device DEVICE       microphone device name
  --latency LATENCY     latency between speech and transcription
  --patience PATIENCE   maximum time to wait for speech before assuming a pause
  --flush               flush the transcribing window, reset the prompt and start a new
                        paragraph after each pause
  --amnesia             only use the last segment instead of the whole paragraph as the
                        prompt for the next segment
  --prompt PROMPT       initial prompt for the first segment
  --deliberation {1,2,3}
                        maximum number of segments to keep in the transcribing window
  --source SOURCE       source language for translation
  --target TARGET       target language for translation
  --tui                 use text-based user interface (curses) instead of graphical user
                        interface (tkinter)
```

## Explanation

The `whispering.py` script listens to the microphone and transcribes the speech in real-time. The transcription is then translated into the target language. The script uses the `fast-whisper` library to perform the transcription and translation.

### Options:

- `--size`: The size of the model to use for transcription and translation. The available sizes are `tiny`, `base`, `small`, `medium`, and `large`.
- `--device`: The name of the microphone device to use for recording.
- `--latency`: The latency between speech and transcription in seconds. The default value is `1.0`.
- `--patience`: The maximum time to wait for speech before assuming a pause in seconds. The default value is `1.0`.
- `--flush`: If present, the script will flush the transcribing window, reset the prompt, and start a new paragraph after each pause. Otherwise the pause time will be simply skipped.
- `--amnesia`: If present, the script will only use the last segment instead of the whole paragraph as the prompt for the next segment. Otherwise the whole paragraph will be used as the prompt.
- `--prompt`: The initial prompt for the first segment in each paragraph.
- `--deliberation`: The maximum number of segments to keep in the transcribing window. The default value is `1`. The higher the value, the more context the model takes into account, but also the higher the processing overhead, which may lead to higher latency.
- `--source`: The source language code for translation. The default value is `None`, which means the source language will be automatically detected.
- `--target`: The target language code for translation. The default value is `en` (English).
- `--tui`: Use text-based user interface (curses is needed) instead of graphical user interface (tkinter is needed).
