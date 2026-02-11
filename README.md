# Whispering

Transcribe and translate speech from a microphone or computer output in real-time, based on the [faster-whisper](https://github.com/SYSTRAN/faster-whisper) module and Google translation service.

## Requirements

- Python 3.11+

## Installation

This repo uses a standard `src/` layout and is installable via `pyproject.toml`.

```bash
pip install .
```

## Usage

After installation, start the GUI with either:

```bash
whispering
```

or:

```bash
python -m whispering
```

![Screenshot](https://github.com/Jemtaly/Whispering/assets/83796250/c68fcd61-752f-4c16-9c13-231ac4b0d2fc)

### GUI Settings

| Option | Description |
| ------ | ----------- |
| **Mic** | Audio input device selection |
| **Model size or path** | Whisper model to use |
| **Device** | Computing device for inference |
| **VAD** | Enable Voice Activity Detection to filter out silence |
| **Memory** | Number of previous confirmed segments to use as prompts for context |
| **Patience** | Minimum time (seconds) to wait after a segment ends before confirming it |
| **Timeout** | HTTP timeout (seconds) for translation requests |
| **Source** | Source language for transcription (`auto` for automatic detection) |
| **Target** | Target language for translation (`none` to disable translation) |
| **Prompt** | Initial prompt text to guide transcription style/vocabulary |

### Display

- **Left panel**: Displays transcription results
- **Right panel**: Displays translation results
- **Black text**: Confirmed, finalized text
- **Blue underlined text**: Draft text still being refined in the transcription window

## Architecture

The project follows a clean, modular architecture with clear separation of concerns:

```
whispering/
├── core/                      # Core abstractions and engine
│   ├── interfaces.py          # Abstract interfaces for all services
│   ├── engine.py              # STTEngine - orchestrates the pipeline
│   └── utils.py               # Shared utilities (MergingQueue, Pair, Data)
├── services/                  # Pluggable service implementations
│   ├── audio/
│   │   └── soundcard_impl.py  # Audio recording via soundcard
│   ├── transcription/
│   │   └── whisper_impl.py    # Transcription via faster-whisper
│   └── translation/
│       └── google_impl.py     # Translation via Google Translate
└── gui.py                     # Tkinter-based GUI application
```

### Core Components

- **Interfaces** (`core/interfaces.py`): Defines abstract base classes for `RecordingService`, `TranscriptionService`, and `TranslationService`, enabling easy extension with custom implementations.

- **STTEngine** (`core/engine.py`): The central orchestrator that manages three parallel threads:
  - **Record thread**: Captures audio frames from the input device
  - **Transcription thread**: Processes audio frames and produces transcription pairs (confirmed + draft text)
  - **Translation thread**: Translates transcription results in real-time

### Service Implementations

- **SoundcardRecordingService**: Records audio using the `soundcard` library, supporting both microphones and loopback (system audio capture).

- **WhisperTranscriptionService**: Uses faster-whisper for transcription with a sliding window approach. Maintains a "transcription window" that accumulates audio until segments are confirmed based on the patience parameter.

- **GoogleTranslationService**: Translates text using Google's translation API with configurable timeout.

### Extensibility

The modular architecture makes it easy to add custom implementations:

1. **Custom Recording Service**: Implement `RecordingService` and `RecordingServiceFactory` interfaces
2. **Custom Transcription Service**: Implement `TranscriptionService` and `TranscriptionServiceFactory` interfaces
3. **Custom Translation Service**: Implement `TranslationService` (or extend `CoreTranslationService`) and `TranslationServiceFactory` interfaces

Example: To use a different translation service, create a new implementation in `services/translation/` that implements the `TranslationService` interface, then update the GUI to use your factory.

## FAQ

### How does the program work?

When the program starts working, it takes the audio stream in real time from the input device (microphone or computer output) and transcribes it. After a piece of audio is transcribed, the corresponding text fragment is obtained and output to the screen immediately.

To avoid inaccurate transcription due to lack of context or speech being cut off mid-sentence, the program uses a "transcription window" mechanism. Segments that have been transcribed but not yet confirmed are displayed as underlined blue text. When the next audio chunk arrives, it's concatenated to the window. The audio in the window is transcribed iteratively, with results constantly revised and updated until a sentence is completed and has sufficient subsequent context (determined by the `patience` parameter) before being confirmed (turning into black text).

The last few confirmed segments (controlled by the `memory` parameter) are used as prompts for subsequent transcription to improve accuracy.

Simultaneously, the real-time transcription fragments are sent to Google Translate, and translation results are displayed in the right panel. Users can specify source and target languages using the respective dropdowns.

### What is the effect of the `patience` and `memory` parameters?

**Patience**: Determines the minimum time to wait for subsequent speech before confirming a segment.
- Too low: May confirm segments too early, resulting in incomplete sentences
- Too high: Creates lag as the transcription window accumulates too much content

**Memory**: Controls how many previous confirmed segments are used as context prompts.
- Too low: Insufficient context may reduce transcription accuracy
- Too high: Overly long prompts may slow down transcription

### What are the advantages of Whispering?

- **Real-time iterative transcription**: Continuously refines results while minimizing delay
- **Smart sentence boundary detection**: Automatically determines optimal points to confirm segments
- **Simultaneous translation**: Get translations in real-time alongside transcription
- **System audio capture**: Can transcribe audio from any application via loopback devices

### Does it need Internet connectivity?

- **Transcription only**: No internet required. Set target language to `none`.
- **With translation**: Internet connection required for Google Translate API.
