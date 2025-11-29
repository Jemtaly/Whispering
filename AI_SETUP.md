# AI Text Processing Setup Guide

This guide explains how to set up and use AI-powered text processing in Whispering for improved transcription formatting, spell correction, and intelligent translation.

## Features

The AI integration provides:

- **Intelligent Translation**: Context-aware translation that understands speech patterns
- **Spell Correction**: Automatically fixes speech recognition errors before translation
- **Proofreading**: Corrects grammar, punctuation, and formatting issues
- **Multiple AI Models**: Choose from various models via OpenRouter (Claude, GPT-4, Gemini, Llama, etc.)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `PyYAML` - for configuration file parsing
- `python-dotenv` - for environment variable management
- All existing Whispering dependencies

### 2. Get an OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up for a free account
3. Visit [API Keys page](https://openrouter.ai/keys)
4. Create a new API key
5. Copy the key (you'll need it in the next step)

**Note**: OpenRouter provides free credits to start testing! You can also use their free models.

### 3. Configure Your API Key

Create a `.env` file in the Whispering directory:

```bash
# Option 1: Copy from example
cp .env.example .env

# Option 2: Create directly
echo "OPENROUTER_API_KEY=your_actual_key_here" > .env
```

**Important**: Replace `your_actual_key_here` with your actual API key!

The `.env` file is automatically git-ignored for security.

### 4. Verify Configuration

Test your configuration:

```bash
python ai_config.py
```

You should see:
```
Testing AI Configuration...

Configuration Status:
  Config file: ✓
  API key: ✓ (env: OPENROUTER_API_KEY)
  Models available: 6
  Default model: anthropic/claude-3-haiku

✓ Configuration is ready!
```

### 5. Test the Provider

Test the OpenRouter connection:

```bash
python ai_provider.py
```

Expected output:
```
Testing OpenRouter Provider...

Using model: anthropic/claude-3-haiku
✓ Connection successful (model: Claude 3 Haiku)

Testing translation mode...
  Input: Hello, how are you today?
  Output: Hola, ¿cómo estás hoy?
✓ Translation test passed
```

## Using AI Features in Whispering

### GUI Mode

1. Start Whispering:
   ```bash
   python gui.py
   ```

2. Configure transcription settings as usual (mic, model, etc.)

3. **Enable AI Processing**:
   - Check the **AI** checkbox
   - Select **Mode**:
     - `Translate`: Direct AI translation (context-aware)
     - `Proofread+Translate`: Fix errors first, then translate
   - Select **Model**: Choose your preferred AI model

4. Set source and target languages as usual

5. Click **Start** and begin speaking!

### What Happens

```
Your Speech
    ↓
Whisper Transcription (speech-to-text)
    ↓
Paragraph Detection (adaptive)
    ↓
AI Processing:
  - Mode: Proofread+Translate
    1. Fix spelling/grammar errors
    2. Translate to target language
  - Mode: Translate
    1. Direct translation with context
    ↓
Formatted, Corrected Translation
```

## Available Models

The default configuration includes these models (via OpenRouter):

| Model | Speed | Best For |
|-------|-------|----------|
| **Claude 3 Haiku** | ⚡ Fastest | Real-time transcription (default) |
| Claude 3.5 Sonnet | Medium | Best accuracy |
| GPT-4 Turbo | Medium | OpenAI's best |
| GPT-3.5 Turbo | Fast | Cost-effective |
| Gemini Pro | Fast | Google's AI |
| Llama 3.1 70B | Medium | Open source |

### Changing Default Model

Edit `ai_config.yaml` and change:

```yaml
defaults:
  model: "anthropic/claude-3-haiku"  # Change this
```

## Configuration Files

### ai_config.yaml

Main configuration file with:
- Available models
- System prompts for translation and proofreading
- Default settings

You can customize the prompts to change how the AI processes text!

### .env

Contains your API key (never commit this file):
```
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

## Troubleshooting

### "AI features not available"

**Cause**: Missing dependencies or configuration

**Solution**:
```bash
# Install dependencies
pip install PyYAML python-dotenv

# Verify ai_config.yaml exists
ls ai_config.yaml

# Check configuration
python ai_config.py
```

### "API key not configured"

**Cause**: `.env` file missing or incorrect

**Solution**:
```bash
# Create .env file
cp .env.example .env

# Edit and add your key
nano .env  # or use your favorite editor

# Verify
cat .env  # Should show: OPENROUTER_API_KEY=your_key
```

### "Authentication error: HTTP 401/403"

**Cause**: Invalid API key

**Solution**:
1. Verify your API key at [OpenRouter Keys](https://openrouter.ai/keys)
2. Make sure you copied it correctly to `.env`
3. Check for extra spaces or quotes

### "Connection error" or "Request timeout"

**Cause**: Network issues or API unavailable

**Solutions**:
- Check your internet connection
- Verify OpenRouter status: https://status.openrouter.ai/
- Try a different model (some may be faster)
- Increase timeout in `ai_config.yaml`:
  ```yaml
  openrouter:
    timeout: 20.0  # Increase from 10.0
  ```

### Slow Performance

**Solutions**:
1. Use a faster model (Claude 3 Haiku is fastest)
2. Use "Translate" mode instead of "Proofread+Translate"
3. Reduce Whisper model size (e.g., use "small" instead of "large-v3")

## Advanced: Custom Prompts

You can customize how AI processes text by editing `ai_config.yaml`:

```yaml
prompts:
  translate:
    system: |
      Your custom translation instructions here...

  proofread_translate:
    system: |
      Your custom proofread+translate instructions here...
```

Variables you can use:
- `{source_lang}` - Source language
- `{target_lang}` - Target language

## Cost Considerations

- **Free Tier**: OpenRouter offers free credits and some free models
- **Pay-as-you-go**: Pricing varies by model
- **Check costs**: https://openrouter.ai/models

**Tip**: Use Claude 3 Haiku or GPT-3.5 Turbo for cost-effective real-time processing.

## Privacy & Security

- API keys are stored in `.env` (git-ignored)
- Your audio is processed by Whisper locally
- Only transcribed text is sent to OpenRouter
- Review OpenRouter's privacy policy: https://openrouter.ai/privacy

## Disable AI Features

To use traditional Google Translate instead:

1. Simply uncheck the "AI" checkbox in the GUI
2. The app will fall back to the original translation method

You can switch between AI and Google Translate at any time!

## Support

- **OpenRouter Issues**: https://openrouter.ai/docs
- **Whispering Issues**: Create an issue on GitHub
- **API Key Problems**: Check OpenRouter documentation

## Examples

### Example 1: English to Spanish (with errors)

**Input** (spoken with errors):
```
Hello my naem is John and I'm a softwere enginear
```

**Mode: Translate**
```
Hola, mi nombre es John y soy ingeniero de software
```

**Mode: Proofread+Translate**
```
Hola, mi nombre es John y soy ingeniero de software
```
(Corrects "naem" → "name" and "softwere enginear" → "software engineer" before translating)

### Example 2: Technical Content

**Input**:
```
We use React hooks like useState and useEffect for state managment
```

**Output** (to Japanese, Proofread+Translate):
```
私たちはReact hooksのuseStateやuseEffectを状態管理に使用しています
```
(Fixes "managment" → "management", preserves technical terms)

---

**Happy transcribing! 🎤**
