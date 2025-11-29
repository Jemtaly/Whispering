# Project Structure

This document describes the organization of the Whispering project.

## Directory Layout

```
Whispering/
├── src/                    # Source code
│   ├── core.py            # Core transcription engine
│   ├── gui.py             # Graphical user interface
│   ├── tui.py             # Terminal user interface
│   ├── ai_config.py       # AI configuration loader
│   ├── ai_provider.py     # AI text processing
│   ├── tts_controller.py  # Text-to-speech controller
│   ├── tts_provider.py    # TTS provider interface
│   ├── autotype.py        # Auto-typing functionality
│   ├── settings.py        # Settings persistence
│   ├── cmque.py           # Custom queue implementation
│   ├── transcript_logger.py # Transcript logging to files
│   ├── debug_audio.py     # Audio debugging utility
│   └── debug_cuda.py      # CUDA debugging utility
│
├── config/                # Configuration files
│   ├── ai_config.yaml     # AI model configuration
│   └── .env.example       # Environment variables template
│
├── scripts/               # Shell scripts
│   ├── install.sh        # Installation script
│   ├── run.sh            # Main launcher script
│   └── debug_env.sh      # Environment debugging
│
├── log_output/           # Transcript log files (gitignored)
│   └── transcript_*.txt  # Auto-generated session logs
│
├── docs/                 # Documentation (in root for visibility)
│   ├── README.md         # Main documentation
│   ├── AI_SETUP.md       # AI features setup guide
│   └── INSTALL_TTS.md    # TTS installation guide
│
├── requirements.txt      # Python dependencies
├── LICENSE              # Project license
└── .gitignore          # Git ignore rules
```

## Key Components

### Source Code (`src/`)
All Python source files are located in the `src/` directory. The main entry points are:
- `gui.py` - Main graphical interface (run with `scripts/run.sh`)
- `tui.py` - Terminal interface (run with `python src/tui.py`)

### Configuration (`config/`)
Configuration files that control application behavior:
- `ai_config.yaml` - AI model settings and prompts
- `.env.example` - Template for environment variables (copy to `.env` in project root)

### Scripts (`scripts/`)
Helper scripts for setup and running the application:
- `install.sh` - Automated installation and setup
- `run.sh` - Launch the GUI with proper environment setup
- `debug_env.sh` - Diagnose CUDA and audio issues

### Log Output (`log_output/`)
Automatically created directory for transcript logs. Files are named:
```
transcript_YYYYMMDD_HHMMSS.txt
```

Each log file includes:
- Session start/end timestamps
- Duration
- Timestamped transcript entries

**Note:** This directory is gitignored to keep your transcripts private.

## Installation

### Quick Install
```bash
./scripts/install.sh
```

The install script will:
- Check Python version (3.8+ required)
- Create virtual environment
- Install all dependencies
- Optionally install CUDA libraries
- Create necessary directories
- Set up .env file from template

## Running the Application

### GUI Mode
```bash
./scripts/run.sh
```

### TUI Mode
```bash
# With logging (default)
python src/tui.py

# Without logging
python src/tui.py --no-log

# List recent logs while running
Press 'L' in TUI
```

## New Features

### Transcript Logging
- **Automatic logging** - All transcriptions are saved to `log_output/`
- **Session-based** - Each start/stop creates a new log file
- **Timestamped** - Each entry includes time of transcription
- **Presentable format** - Includes headers, footers, and session duration

### TUI Enhancements
- Press `L` to list recent log files
- Status shows "(Logging)" when recording
- Clean session management

## Development

### Adding Dependencies
```bash
# Activate virtual environment
source .venv/bin/activate

# Install new package
pip install package_name

# Update requirements
pip freeze > requirements.txt
```

### File Organization Rules
- All Python code goes in `src/`
- Configuration files go in `config/`
- Shell scripts go in `scripts/`
- Documentation stays in root (for GitHub visibility)
- User-generated files (logs, settings) are gitignored

## Migration Notes

If you have an existing installation, the file reorganization is backward-compatible:
- `run.sh` now sets `PYTHONPATH` to include `src/`
- Config paths are automatically resolved relative to installation directory
- User settings file (`whispering_settings.json`) remains in project root
