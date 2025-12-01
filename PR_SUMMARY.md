# Pull Request: Fix UI layout, add custom AI personas, and implement manual trigger mode

**Branch:** `claude/fix-ui-layout-scrollbar-018sMwXYfVYMrBZCcaiKfmxe`
**Base:** `main`

## Summary

This PR addresses multiple UI/UX issues and adds significant new functionality to the Whispering application's AI processing system.

### 🐛 Bug Fixes

**UI Layout Issues:**
- Fixed second column merging into first column in some display configurations
- Added scrollbars to all three text output windows (Whisper, AI Output, Translation)
- Removed incorrect `rowconfigure(1)` that caused layout problems

**Output Routing:**
- Fixed proofreading output incorrectly going to translation window
- Corrected `prres_queue` initialization for proofread-only mode
- Fixed output routing logic in `core.py` to send results to correct queues

**Settings Persistence:**
- Fixed AI interval settings reverting to defaults (20 seconds)
- Fixed AI words threshold not persisting
- Fixed auto-stop settings not being saved
- Added comprehensive settings save in `on_closing()`

**Auto-Stop Logic:**
- Changed from runtime-based to inactivity-based timeout
- Now only triggers when configured AND no new input detected
- Made completely optional (disabled by default)

### ✨ New Features

**Custom AI Personas System:**
- Added support for user-defined AI processing tasks
- Created `config/custom_personas.yaml.example` with sample personas (Story Narrator, Meeting Notes, Code Documentation)
- Extended `ai_config.py` to load custom personas from separate config file
- Added `config/custom_personas.yaml` to `.gitignore` for user customization
- Built-in "Proofread" persona always available
- Each persona can have custom system prompts and descriptions

**Manual Trigger Mode:**
- Added "Manual mode" checkbox for on-demand AI processing
- Added "⚡ Process Now" button to trigger processing when ready
- Implemented mutually exclusive UI behavior:
  - Manual mode enabled: Process Now button active, automatic triggers disabled
  - Manual mode disabled: Process Now button disabled, automatic triggers active
- Clear left/right split layout separating manual and automatic controls
- Manual trigger flag properly passed to `core.py` processing pipeline

**Translate-Only Mode:**
- Added "Translate Only (1:1)" checkbox for direct translation without AI processing
- Disables Task and Translate output checkboxes when enabled
- Provides simple 1:1 translation similar to Google Translate

**Configurable Auto-Stop:**
- Added GUI controls: checkbox and spinbox below level indicator
- Configurable timeout: 1-60 minutes of inactivity
- Disabled by default (user must explicitly enable)
- Settings properly persisted across sessions

**UI Improvements:**
- Renamed "Proofread Output" to "AI Output" (more generic, supports custom personas)
- Redesigned AI controls section with clearer layout
- Changed "sec:" label to "Interval:" for clarity
- Moved interval/words controls to separate row for better organization
- Removed confusing "None" option from personas list

### 🔧 Technical Changes

**Modified Files:**
- `src/gui.py`: Major UI redesign, added manual mode controls, settings persistence
- `src/core.py`: Manual trigger support, skip auto triggers in manual mode, fixed output routing
- `src/ai_config.py`: Custom personas loading, persona management methods
- `src/settings.py`: Added settings for personas, translate modes, manual mode, auto-stop
- `config/custom_personas.yaml.example`: Example custom personas template (new file)
- `.gitignore`: Added `config/custom_personas.yaml`
- `README.md`: Comprehensive documentation of all new features

**Key Implementation Details:**
- Manual mode sets `ai_trigger_mode = "manual"` to skip automatic triggers
- `on_trigger_mode_changed()` handler manages UI state transitions
- Manual trigger uses shared flag `[False]` for thread-safe communication
- Custom personas merged with built-in personas in unified dropdown
- Settings persistence includes all new configuration options

**File Statistics:**
```
 .gitignore                          |   1 +
 README.md                           |  69 ++++--
 config/custom_personas.yaml.example |  50 ++++
 src/ai_config.py                    |  65 ++++++
 src/core.py                         |  60 +++--
 src/gui.py                          | 449 +++++++++++++++++++++++++++++-------
 src/settings.py                     |  10 +-
 7 files changed, 573 insertions(+), 131 deletions(-)
```

### 📝 Testing

All Python files compile without syntax errors:
- ✅ `src/gui.py`
- ✅ `src/core.py`
- ✅ `src/settings.py`
- ✅ `src/ai_config.py`

### 🎯 User-Requested Features

All originally requested features have been implemented:
- ✅ Fixed UI layout issues and added scrollbars
- ✅ Fixed proofreading output routing
- ✅ Implemented configurable auto-stop with GUI controls
- ✅ Fixed settings persistence
- ✅ Added manual trigger button
- ✅ Implemented custom personas system
- ✅ Redesigned AI controls with checkboxes
- ✅ Added manual mode toggle with left/right split layout
- ✅ Added translate-only mode
- ✅ Updated documentation

## Commits

1. `c040222` - fix: comprehensive UI and AI processing improvements
2. `0edbc85` - feat: add custom AI personas, manual trigger, and improved UI controls
3. `0f28502` - fix: redesign AI controls for clarity and add translate-only mode
4. `0c711ef` - feat: add manual mode toggle for AI trigger control
5. `b8cfe85` - docs: update README with new AI features and UI improvements

## Test Plan

- [ ] Verify scrollbars appear on all three text windows
- [ ] Test manual mode: checkbox enables Process Now button, disables automatic triggers
- [ ] Test automatic mode: checkbox disables Process Now button, enables automatic triggers
- [ ] Verify custom personas load from `custom_personas.yaml` (copy from example file)
- [ ] Test translate-only mode: checkbox disables Task and Translate output options
- [ ] Verify auto-stop: only triggers when enabled AND after configured inactivity period
- [ ] Confirm settings persist across application restarts
- [ ] Test proofread output goes to AI Output window (not Translation)
- [ ] Verify manual trigger processes accumulated text immediately

## Screenshots

The new UI layout features:

**Manual Mode (Left Side):**
- ☑ Manual mode checkbox
- ⚡ Process Now button (enabled when manual mode checked)

**Automatic Mode (Right Side):**
- Trigger: [Time ▼]
- Interval: [20s ▼]  words: [150]

**Text Windows:**
All three windows now have scrollbars and proper enable/disable visual feedback.

## Breaking Changes

None. All changes are backward compatible. Existing settings files will be automatically migrated with new default values.

## Related Issues

This PR addresses the following issues reported by the user:
1. UI layout problems with column merging and missing scrollbars
2. Incorrect output routing for proofread-only mode
3. Auto-stop triggering after fixed 5 minutes with no configuration
4. Settings reverting to defaults after changes
5. Need for manual trigger option
6. Request for custom AI personas system
7. Confusing UI with both manual and automatic triggers visible simultaneously
