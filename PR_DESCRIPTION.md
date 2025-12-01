# Pull Request: Add Target Language Persistence and Debug Output Control

## Summary

This PR adds two new features to improve user experience and debugging capabilities:

1. **Target Language Persistence** - Translation source and target language selections are now saved and restored across application restarts
2. **Debug Output Control** - Centralized debug logging system controlled via settings file

## Changes

### Target Language Persistence
- Save and load source/target language settings from `whispering_settings.json`
- Languages are automatically restored when the application starts (gui.py:726-741)
- Changes saved when application closes (gui.py:1242-1249)

### Debug Output Control
- Created new `debug.py` module with centralized debug output control
- All debug messages now controlled by `debug_enabled` setting in settings file
- Updated `gui.py`, `text_widget.py`, and `processing.py` to use debug system
- Debug output includes prefixes (`[GUI]`, `[TEXT-*]`, `[DEBUG]`, `[INFO]`) for easy filtering
- Debug mode is disabled by default for clean console output

## Configuration

Users can enable debug mode by editing `whispering_settings.json`:
```json
{
  "debug_enabled": true
}
```

Debug output will show:
- AI trigger mode and intervals
- Proofread window state changes
- Text queue operations
- Manual AI processing requests
- Auto-stop events

## Documentation

- Updated README with Configuration section explaining settings persistence and debug mode
- Added `debug.py` to file structure documentation
- Documented all debug output categories and how to enable/disable

## Testing

✅ Verified target language persistence across application restarts
✅ Tested debug output control (enabled/disabled states)
✅ Confirmed all debug messages are properly controlled
✅ No syntax errors in modified files
✅ All imports work correctly

## Files Modified

- `src/gui.py` - Load/save target languages, debug flag support
- `src/gui_parts/text_widget.py` - Use debug_print for queue logging
- `src/core_parts/processing.py` - Use debug_print for all debug messages
- `src/debug.py` - **New file** - Debug control module
- `README.md` - Documentation updates

## Commits

1. `09eb590` - feat: Add target language persistence and debug output control
2. `8d7b9b5` - docs: Update README with new configuration features

## Branch

`claude/fix-translation-target-language-01DCfFCf8qRF8vok7V9dmLAw`

---

**Note:** As requested, this PR does not attempt to push to master/main. Please review and merge at your convenience.
