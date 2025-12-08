# Whispering

Transcribe and translate speech from a microphone or computer output in real-time, based on the [fast-whisper](https://github.com/SYSTRAN/faster-whisper) module and Google translation service.

## Requirements

- Python 3.8+
- [Soundcard](https://pypi.org/project/SoundCard/)
- [fast-whisper](https://github.com/SYSTRAN/faster-whisper)
- [requests](https://pypi.org/project/requests/)

## Usage

Simply run the `gui.py` script to start the GUI version of the program.

![Screenshot](https://github.com/Jemtaly/Whispering/assets/83796250/c68fcd61-752f-4c16-9c13-231ac4b0d2fc)

## Q&A

- How does the program work?

  When the program starts working, it will take the audio stream in real time from the input device (microphone or computer output) and transcribe it. After a piece of audio is transcribed, the corresponding text fragment will be obtained and output to the screen immediately. In order to avoid inaccurate transcription results due to lack of context or speech being cut off in the middle, the program will temporarily place the segments that have been transcribed but have not yet been fully confirmed in a "transcription window" (displayed as underlined blue text in the GUI app). When the next piece of audio comes, it will be concatenated to the window. The audio in the window is transcribed iteratively, and the transcription results are constantly revised and updated until a sentence is completed and has sufficient subsequent context (determined by the `patience` parameter) before it is moved out of the transcription window (turns into black text). The last few moved-out segments (the number is determined by the `memory` parameter) will be used as prompts for subsequent context to improve the accuracy of transcription.

  At the same time, the real-time transcription text fragments will be sent to the Google translation service for translation, and the translation results will also be output to the screen in real time. Users can specify the source language and target language by setting the `source` and `target` parameters. If the source language is not specified, the program will automatically detect the source language. If the target language is not specified, no translation will be performed.

- What is the effect of the `patience` and `memory` parameters on the program?

  The `patience` parameter determines the minimum time to wait for subsequent speech before moving a completed segment out of the transcription window. If the `patience` parameter is set too low, the program may move the segment out of the window too early, resulting in incomplete sentences or inaccurate transcription. If the `patience` parameter is set too high, the program may wait too long to move the segment out of the window, this will cause the transcription window to accumulate too much content, which may result in slower transcription speed.

  The `memory` parameter determines the maximum number of previous segments to be used as prompts for audio in the transcription window. If the `memory` parameter is set too low, the program may not have enough previous context used as prompts, which may result in inaccurate transcription. If the `memory` parameter is set too high, the prompts could be too long, which also could slow down the transcription speed.

- What are the advantages of Whispering compared to other speech recognition programs based on Whisper?

  Since the program iteratively transcribes the audio in real time and can automatically divide the sentence at the appropriate position to move it out of the transcription window, Whispering can ensure the accuracy of recognition while minimizing the delay caused by the accumulation of audio. In addition, Whispering also supports real-time translation, allowing users to obtain translation results while transcribing, which is very useful in scenarios that require multilingual support.

- Does it need to be connected to the Internet?

  If you only need the real-time transcription function, then it does not need to be connected to the Internet. In this case, you only need to set the target language for translation to `none`. However, if you need the translation function, then an Internet connection is necessary. Because in the current implementation, the translation function is implemented by calling Google's translation service.

- About scalability

  The core logic of the program is in `core.py`, where the logic of transcription and translation is clearly separated, so you can extend or modify it as needed. For example, you can replace the translation service with other translation services.
