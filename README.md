# Whispering

Transcribe and translate speech from a microphone or computer output in real-time, based on the [fast-whisper](https://github.com/SYSTRAN/faster-whisper) library and Google translation service. Both GUI and TUI versions are available.

## Requirements

- Python 3.8+
- [fast-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition)
- [PyAudio](https://pypi.org/project/PyAudio) 0.2.11+
- If you want to transcript from computer output, you can use virtual audio cable such as [VB-Audio Virtual Cable](https://vb-audio.com/Cable) or [Jack Audio Connection Kit](https://jackaudio.org), or use the `loopback` device in PulseAudio or ALSA.

## Usage

The program is available in both GUI and TUI versions.

- GUI

Simply run the `gui.py` script to start the GUI version of the program.

![Screenshot](https://github.com/Jemtaly/Whispering/assets/83796250/c68fcd61-752f-4c16-9c13-231ac4b0d2fc)

- TUI

```
usage: tui.py [-h] [--mic MIC] [--model MODEL] [--vad]
              [--memory MEMORY] [--patience PATIENCE] [--timeout TIMEOUT]
              [--prompt PROMPT] [--source SOURCE] [--target TARGET]

Transcribe and translate speech in real-time.

options:
  -h, --help            show this help message and exit
  --mic MIC             microphone device name
  --model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}
                        size of the model to use
  --vad                 enable voice activity detection
  --memory MEMORY       maximum number of previous segments to be used as prompt for audio
                        in the transcribing window
  --patience PATIENCE   minimum time to wait for subsequent speech before move a completed
                        segment out of the transcribing window
  --timeout TIMEOUT     timeout for the translation service
  --prompt PROMPT       initial prompt for the first segment of each paragraph
  --source {af,am,ar,as,az,ba,be,bg,bn,bo,br,bs,ca,cs,cy,da,de,el,en,es,et,eu,fa,fi,fo,fr,gl,gu,ha,haw,he,hi,hr,ht,hu,hy,id,is,it,ja,jw,ka,kk,km,kn,ko,la,lb,ln,lo,lt,lv,mg,mi,mk,ml,mn,mr,ms,mt,my,ne,nl,nn,no,oc,pa,pl,ps,pt,ro,ru,sa,sd,si,sk,sl,sn,so,sq,sr,su,sv,sw,ta,te,tg,th,tk,tl,tr,tt,uk,ur,uz,vi,yi,yo,yue,zh}
                        source language for translation, auto-detect if not specified
  --target {af,ak,am,ar,as,ay,az,be,bg,bho,bm,bn,bs,ca,ceb,ckb,co,cs,cy,da,de,doi,dv,ee,el,en,eo,es,et,eu,fa,fi,fil,fr,fy,ga,gd,gl,gn,gom,gu,ha,haw,he,hi,hmn,hr,ht,hu,hy,id,ig,ilo,is,it,ja,jw,ka,kk,km,kn,ko,kri,ku,ky,la,lb,lg,ln,lo,lt,lus,lv,mai,mg,mi,mk,ml,mn,mni-Mtei,mr,ms,mt,my,ne,nl,no,nso,ny,om,or,pa,pl,ps,pt,qu,ro,ru,rw,sa,sd,si,sk,sl,sm,sn,so,sq,sr,st,su,sv,sw,ta,te,tg,th,ti,tk,tl,tr,ts,tt,ug,uk,ur,uz,vi,xh,yi,yo,zh-CN,zh-TW,zu}
                        target language for translation, no translation if not specified
```

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
