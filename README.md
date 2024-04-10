# Whispering
A real-time transcription and translation tool implemented in Python based on the [fast-whisper](https://github.com/SYSTRAN/faster-whisper) library.

## Requirements

- Python 3.8+
- [fast-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition)
- [PyAudio](https://pypi.org/project/PyAudio) 0.2.11+

## Usage

```
usage: gui.py [-h] [--mic MIC]
              [--model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}]
              [--memory MEMORY] [--patience PATIENCE] [--timeout TIMEOUT]

Transcribe and translate speech in real-time.

options:
  -h, --help            show this help message and exit
  --mic MIC             microphone device name
  --model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}
                        size of the model to use
  --memory MEMORY       maximum number of previous segments to be used as prompt for audio
                        in the transcribing window
  --patience PATIENCE   minimum time to wait for subsequent speech before move a completed
                        segment out of the transcribing window
  --timeout TIMEOUT     timeout for the translation service
```

```
usage: tui.py [-h] [--mic MIC]
              [--model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}]
              [--memory MEMORY] [--patience PATIENCE] [--timeout TIMEOUT]
              [--prompt PROMPT] [--source SOURCE] [--target TARGET]

Transcribe and translate speech in real-time.

options:
  -h, --help            show this help message and exit
  --mic MIC             microphone device name
  --model {tiny,base,small,medium,large-v1,large-v2,large-v3,large}
                        size of the model to use
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
