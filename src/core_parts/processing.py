import collections
import threading
import time
from urllib.parse import quote
import numpy as np
import requests
import sounddevice as sd
from cmque import DataDeque, PairDeque, Queue
from faster_whisper import WhisperModel
from debug import debug_print

# Import AI modules
try:
    from ai_config import AIConfig
    from ai_provider import AITextProcessor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

from .paragraph_detector import ParagraphDetector
from .audio_devices import (
    TARGET_SAMPLE_RATE, SAMPLE_WIDTH, CHUNK_DURATION,
    get_default_device_index, get_device_info, audio_to_wav_bytes, resample_to_mono_16k
)

def translate(text, source, target, timeout):
    if target is None:
        # No target language specified - return empty to show nothing in translation output
        return []
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}".format(source or "auto", target, quote(text))
        ans = requests.get(url, timeout=timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except:
        return [(text, "Translation service is unavailable.")]


def parse_ai_proofread_translate(text):
    """
    Parse AI output when using proofread+translate mode.

    Expected format:
    PROOFREAD:
    [corrected text]

    TRANSLATE:
    [translated text]

    Returns:
        (proofread_text, translate_text) tuple
        If parsing fails, returns ("", text) to show translation only
    """
    if not text:
        return ("", "")

    # Try to parse the structured output
    text_upper = text.upper()

    # Look for PROOFREAD: and TRANSLATE: markers
    proofread_marker = text_upper.find("PROOFREAD:")
    translate_marker = text_upper.find("TRANSLATE:")

    if proofread_marker != -1 and translate_marker != -1:
        # Both markers found - extract sections
        proofread_start = proofread_marker + len("PROOFREAD:")
        proofread_end = translate_marker

        proofread_text = text[proofread_start:proofread_end].strip()
        translate_text = text[translate_marker + len("TRANSLATE:"):].strip()

        return (proofread_text, translate_text)

    elif translate_marker != -1:
        # Only TRANSLATE marker found - might be translate-only mode
        translate_text = text[translate_marker + len("TRANSLATE:"):].strip()
        return ("", translate_text)

    elif proofread_marker != -1:
        # Only PROOFREAD marker found - might be proofread-only mode
        proofread_text = text[proofread_marker + len("PROOFREAD:"):].strip()
        return (proofread_text, "")

    else:
        # No markers found - treat entire text as translation
        # (AI might have returned only the translated text)
        return ("", text)


def ai_translate(text, ai_processor):
    """
    Translate/process text using AI provider.

    Args:
        text: Text to process
        ai_processor: AITextProcessor instance

    Returns:
        (processed_text, error_message) tuple
    """
    if not text or not text.strip():
        return ("", None)

    try:
        result, error = ai_processor.process(text)
        return (result, error)
    except Exception as e:
        return (text, f"AI processing error: {str(e)}")


def proc(index, model, vad, memory, patience, timeout, prompt, source, target, tsres_queue, tlres_queue, ready, device="cpu", error=None, level=None, para_detect=True, para_threshold_std=1.5, para_min_pause=0.8, para_max_chars=500, para_max_words=100, ai_processor=None, ai_process_interval=2, ai_process_words=None, ai_trigger_mode="time", silence_timeout=60, prres_queue=None, auto_stop_enabled=False, auto_stop_minutes=5, manual_trigger=None):
    # Create paragraph detector if enabled
    para_detector = ParagraphDetector(
        threshold_std=para_threshold_std,
        min_pause=para_min_pause,
        max_chars=para_max_chars,
        max_words=para_max_words
    ) if para_detect else None
    
    def ts_proc():
        prompts = collections.deque([prompt], memory)
        window = bytearray()
        cumulative_offset = 0.0  # Track total trimmed audio in seconds
        
        while frame := frame_queue.get():
            window.extend(frame)
            audio_file = audio_to_wav_bytes(window, TARGET_SAMPLE_RATE, SAMPLE_WIDTH, channels=1)
            segments, info = whisper_model.transcribe(audio_file, language=source, initial_prompt="".join(prompts), vad_filter=vad)
            segments = [segment for segment in segments]
            start = max(len(window) // SAMPLE_WIDTH / TARGET_SAMPLE_RATE - patience, 0.0)
            i = 0
            for segment in segments:
                if segment.end >= start:
                    if segment.start < start:
                        start = segment.start
                    break
                i += 1
            
            # Process done segments with paragraph detection
            done_segments = segments[:i]
            if para_detector and done_segments:
                # Pass cumulative offset so detector can compute absolute timestamps
                done_src = para_detector.process_segments(done_segments, cumulative_offset)
            else:
                done_src = "".join(segment.text for segment in done_segments)
            
            curr_src = "".join(segment.text for segment in segments[i:])
            prompts.extend(segment.text for segment in done_segments)
            
            # Update cumulative offset BEFORE trimming (start = seconds to trim)
            cumulative_offset += start
            
            del window[: int(start * TARGET_SAMPLE_RATE) * SAMPLE_WIDTH]
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(None)
        tsres_queue.put(None)

    def tl_proc():
        import time

        rsrv_src = ""
        accumulated_done = ""  # Accumulate done text before processing
        last_curr_src = ""  # Track last curr_src for exit processing
        last_process_time = time.time()  # Track when we last processed
        last_activity_time = time.time()  # Track when we last received text
        start_time = time.time()  # Track total runtime for auto-stop

        MIN_CHARS_TO_PROCESS = 150  # Minimum characters before AI processing
        MAX_CHARS_TO_ACCUMULATE = 400  # Force processing if text gets too long
        PROCESS_INTERVAL_SECONDS = ai_process_interval if ai_trigger_mode == "time" else float('inf')  # Already in seconds
        PROCESS_WORD_COUNT = ai_process_words if ai_trigger_mode == "words" and ai_process_words else float('inf')
        SILENCE_TIMEOUT = silence_timeout  # Flush after this many seconds of silence
        AUTO_STOP_DURATION = auto_stop_minutes * 60 if auto_stop_enabled else float('inf')  # Convert minutes to seconds

        while ts2tl := ts2tl_queue.get():
            done_src, curr_src = ts2tl

            # Track last curr_src for exit processing
            last_curr_src = curr_src

            # Check for auto-stop (only if enabled AND no activity for specified duration)
            if auto_stop_enabled and (time.time() - last_activity_time >= AUTO_STOP_DURATION):
                debug_print(f"[INFO] Auto-stopping after {auto_stop_minutes} minutes of inactivity", flush=True)
                ready[0] = False  # Signal stop
                break

            # Use AI processing if available
            if ai_processor:
                # Accumulate done text
                if done_src:
                    accumulated_done += done_src
                    last_activity_time = time.time()  # Update activity time when text arrives

                # Determine if we should process accumulated text
                # Multiple conditions - any one triggers processing:
                has_paragraph_break = '\n\n' in accumulated_done
                has_min_chars = len(accumulated_done) >= MIN_CHARS_TO_PROCESS
                has_max_chars = len(accumulated_done) >= MAX_CHARS_TO_ACCUMULATE

                # Manual trigger - process immediately when requested
                manual_trigger_requested = manual_trigger and manual_trigger[0]
                if manual_trigger_requested and accumulated_done:
                    debug_print("[DEBUG] Manual AI trigger detected, processing immediately", flush=True)
                    manual_trigger[0] = False  # Reset flag

                # Determine automatic triggers based on mode
                if ai_trigger_mode == "manual":
                    # Manual mode: only process on manual trigger, skip all automatic triggers
                    time_threshold_reached = False
                    word_threshold_reached = False
                    silence_threshold_reached = False
                else:
                    # Automatic mode: enable configured triggers
                    # Time-based trigger (only active when trigger_mode == "time")
                    time_elapsed = time.time() - last_process_time
                    time_threshold_reached = time_elapsed >= PROCESS_INTERVAL_SECONDS

                    # Word count trigger (only active when trigger_mode == "words")
                    word_count = len(accumulated_done.split()) if accumulated_done else 0
                    word_threshold_reached = word_count >= PROCESS_WORD_COUNT

                    # Silence timeout trigger - flush if no activity for SILENCE_TIMEOUT seconds
                    silence_elapsed = time.time() - last_activity_time
                    silence_threshold_reached = silence_elapsed >= SILENCE_TIMEOUT and len(accumulated_done.strip()) > 0

                # Process if ANY of these conditions are met:
                # 1. Normal case: 150+ chars AND paragraph break (automatic only)
                # 2. Fallback case 1: 400+ chars (even without paragraph break) (automatic only)
                # 3. Fallback case 2: Time threshold reached (when in time mode)
                # 4. Fallback case 3: Word count threshold reached (when in words mode)
                # 5. Fallback case 4: Silence timeout reached (no speech for X seconds)
                # 6. Fallback case 5: Manual trigger requested
                should_process = (
                    accumulated_done and
                    ((has_min_chars and has_paragraph_break) or
                     has_max_chars or
                     time_threshold_reached or
                     word_threshold_reached or
                     silence_threshold_reached or
                     manual_trigger_requested)
                )

                if should_process:
                    if has_paragraph_break:
                        # Split on paragraph breaks
                        parts = accumulated_done.split('\n\n')
                        # Keep last part (incomplete paragraph) in accumulated_done
                        to_process = '\n\n'.join(parts[:-1])
                        accumulated_done = parts[-1]
                    else:
                        # No paragraph break - process everything (hit max threshold or time/words)
                        to_process = accumulated_done
                        accumulated_done = ""

                    if to_process:
                        # Process with AI - DETAILED DEBUG
                        debug_print(f"\n[DEBUG] ========== CONDITION CHECK ==========", flush=True)
                        debug_print(f"[DEBUG] 1. prres_queue = {prres_queue}", flush=True)
                        debug_print(f"[DEBUG]    prres_queue is not None = {prres_queue is not None}", flush=True)
                        debug_print(f"[DEBUG]    prres_queue bool = {bool(prres_queue)} (NOTE: Queue.__bool__ returns False when empty!)", flush=True)
                        debug_print(f"[DEBUG] 2. ai_processor = {ai_processor}", flush=True)
                        debug_print(f"[DEBUG]    ai_processor bool = {bool(ai_processor)}", flush=True)
                        if ai_processor:
                            debug_print(f"[DEBUG] 3. ai_processor.mode = '{ai_processor.mode}'", flush=True)
                            debug_print(f"[DEBUG]    mode == 'proofread_translate' = {ai_processor.mode == 'proofread_translate'}", flush=True)
                        debug_print(f"[DEBUG] 4. AI_AVAILABLE = {AI_AVAILABLE}", flush=True)

                        # Check combined condition (FIX: use 'is not None' instead of bool check!)
                        combined = bool(prres_queue is not None and ai_processor and ai_processor.mode == "proofread_translate" and AI_AVAILABLE)
                        debug_print(f"[DEBUG] 5. COMBINED CONDITION = {combined}", flush=True)
                        debug_print(f"[DEBUG] ======================================\n", flush=True)

                        if prres_queue is not None and ai_processor and ai_processor.mode == "proofread_translate" and AI_AVAILABLE:
                            # Make TWO separate calls for proofread+translate mode
                            debug_print(f"[DEBUG] ========== EXECUTING TWO-CALL AI PROCESSING ==========", flush=True)
                            debug_print(f"[DEBUG] Input text: {to_process[:100]}...", flush=True)

                            # FIRST CALL: Proofread only
                            debug_print(f"[DEBUG] STEP 1: Creating proofread-only processor", flush=True)
                            config = AIConfig()
                            proofread_processor = AITextProcessor(
                                config=config,
                                model_id=ai_processor.provider.model_id,
                                mode="proofread",  # Use proofread-only mode
                                source_lang=ai_processor.source_lang,
                                target_lang=None
                            )
                            debug_print(f"[DEBUG] STEP 2: Calling AI for proofread", flush=True)
                            proofread_text, pr_error = ai_translate(to_process, proofread_processor)
                            debug_print(f"[DEBUG] STEP 3: Proofread result: '{proofread_text[:150]}'...", flush=True)
                            if pr_error:
                                debug_print(f"[DEBUG] Proofread Error: {pr_error}", flush=True)

                            # SECOND CALL: Translate the proofread text
                            debug_print(f"[DEBUG] STEP 4: Creating translate-only processor", flush=True)
                            translate_processor = AITextProcessor(
                                config=config,
                                model_id=ai_processor.provider.model_id,
                                mode="translate",  # Use translate-only mode
                                source_lang=ai_processor.source_lang,
                                target_lang=ai_processor.target_lang
                            )
                            debug_print(f"[DEBUG] STEP 5: Calling AI for translation (input=proofread text)", flush=True)
                            translate_text, tr_error = ai_translate(proofread_text, translate_processor)
                            debug_print(f"[DEBUG] STEP 6: Translation result: '{translate_text[:150]}'...", flush=True)
                            if tr_error:
                                debug_print(f"[DEBUG] Translation Error: {tr_error}", flush=True)

                            # Determine separators - use paragraph breaks for proofread for better readability
                            # Use smart separator for translation (paragraph break or space)
                            proofread_separator = '\n\n'  # Always use paragraph breaks for proofread output
                            translation_separator = '\n\n' if has_paragraph_break else ' '
                            last_process_time = time.time()  # Reset timer after processing

                            # Send proofread to pr queue, translation to tl queue
                            debug_print(f"[DEBUG] STEP 7: Sending to queues...", flush=True)
                            debug_print(f"[DEBUG]   - Sending proofread ({len(proofread_text)} chars) to PR_QUEUE", flush=True)
                            debug_print(f"[DEBUG]   - Sending translation ({len(translate_text)} chars) to TL_QUEUE", flush=True)
                            if proofread_text:
                                prres_queue.put((proofread_text + proofread_separator, ""))
                                debug_print(f"[DEBUG]   ✓ Sent to PR_QUEUE", flush=True)
                            if translate_text:
                                tlres_queue.put((translate_text + translation_separator, ""))
                                debug_print(f"[DEBUG]   ✓ Sent to TL_QUEUE", flush=True)
                            debug_print(f"[DEBUG] ========== TWO-CALL PROCESSING COMPLETE ==========", flush=True)
                        else:
                            # Single AI call (proofread-only or translate-only)
                            debug_print(f"[DEBUG] Using SINGLE AI call (mode: {ai_processor.mode if ai_processor else 'None'})", flush=True)
                            processed, ai_error = ai_translate(to_process, ai_processor)
                            if ai_error:
                                # Log error to console but continue with result
                                print(f"AI Error: {ai_error}", flush=True)

                            # Determine separator based on context
                            separator = '\n\n' if has_paragraph_break else ' '
                            last_process_time = time.time()  # Reset timer after processing

                            # Send the NEW processed chunk to the correct queue based on mode
                            if ai_processor.mode == "proofread" and prres_queue is not None:
                                debug_print(f"[DEBUG] Sending proofread result to PR_QUEUE", flush=True)
                                prres_queue.put((processed + separator, ""))
                            else:
                                debug_print(f"[DEBUG] Sending result to TL_QUEUE", flush=True)
                                tlres_queue.put((processed + separator, ""))
            else:
                # Use original Google Translate
                if done_src or rsrv_src:
                    done_src = rsrv_src + done_src
                    done_snt = translate(done_src, source, target, timeout)
                    # Only pop reserve if we have multiple segments
                    if len(done_snt) > 1:
                        rsrv_src = done_snt.pop()[0]
                        done_tgt = "".join(t for s, t in done_snt)
                    elif len(done_snt) == 1:
                        # Don't pop if only one segment - use it all
                        done_tgt = done_snt[0][1]
                        rsrv_src = ""
                    else:
                        # Empty translation result
                        done_tgt = ""
                        rsrv_src = ""
                else:
                    done_tgt = ""
                curr_src = rsrv_src + curr_src
                curr_snt = translate(curr_src, source, target, timeout)
                curr_tgt = "".join(t for s, t in curr_snt)
                tlres_queue.put((done_tgt, curr_tgt))

        # Process any remaining accumulated text on exit
        # Combine accumulated_done with last_curr_src to ensure nothing is lost
        final_text = accumulated_done
        if last_curr_src and last_curr_src.strip():
            debug_print(f"[DEBUG] EXIT: Found curr_src text: '{last_curr_src.strip()}'", flush=True)
            final_text = accumulated_done + last_curr_src

        if ai_processor and final_text and final_text.strip():
            debug_print(f"[DEBUG] EXIT: Processing remaining text ({len(final_text)} chars)", flush=True)
            debug_print(f"[DEBUG] EXIT: Text = '{final_text[:200]}'...", flush=True)
            if prres_queue is not None and ai_processor.mode == "proofread_translate" and AI_AVAILABLE:
                # Make TWO separate calls for proofread+translate mode
                debug_print(f"[DEBUG] EXIT: Using two-call processing", flush=True)
                config = AIConfig()
                proofread_processor = AITextProcessor(
                    config=config,
                    model_id=ai_processor.provider.model_id,
                    mode="proofread",
                    source_lang=ai_processor.source_lang,
                    target_lang=None
                )

                proofread_text, _ = ai_translate(final_text, proofread_processor)
                debug_print(f"[DEBUG] EXIT: Proofread result: '{proofread_text[:100]}'", flush=True)

                translate_processor = AITextProcessor(
                    config=config,
                    model_id=ai_processor.provider.model_id,
                    mode="translate",
                    source_lang=ai_processor.source_lang,
                    target_lang=ai_processor.target_lang
                )

                translate_text, _ = ai_translate(proofread_text, translate_processor)
                debug_print(f"[DEBUG] EXIT: Translation result: '{translate_text[:100]}'", flush=True)

                if proofread_text:
                    prres_queue.put((proofread_text, ""))
                    debug_print(f"[DEBUG] EXIT: Sent proofread to PR_QUEUE", flush=True)
                if translate_text:
                    tlres_queue.put((translate_text, ""))
                    debug_print(f"[DEBUG] EXIT: Sent translation to TL_QUEUE", flush=True)
            else:
                # Single AI call
                debug_print(f"[DEBUG] EXIT: Using single AI call", flush=True)
                final_tgt, _ = ai_translate(final_text, ai_processor)
                tlres_queue.put((final_tgt, ""))

        tlres_queue.put(None)
        if prres_queue:
            prres_queue.put(None)

    try:
        # Load model first (before opening audio stream)
        whisper_model = WhisperModel(model, device=device)
        
        # Use smart default if no device specified
        if index is None:
            index = get_default_device_index()
        
        # Query device capabilities
        sample_rate, channels = get_device_info(index)
        chunk_size = int(sample_rate * CHUNK_DURATION)
        
        frame_queue = Queue(DataDeque())
        ts2tl_queue = Queue(PairDeque())
        ts_thread = threading.Thread(target=ts_proc)
        tl_thread = threading.Thread(target=tl_proc)
        
        # Open audio stream with sounddevice
        with sd.InputStream(
            device=index,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=chunk_size
        ) as stream:
            ts_thread.start()
            tl_thread.start()
            ready[0] = True
            
            while ready[0]:
                data, overflowed = stream.read(chunk_size)
                # Make a copy immediately to avoid memory issues
                data_copy = np.array(data, copy=True)
                
                # Calculate audio level (RMS) for the level meter
                if level is not None:
                    rms = np.sqrt(np.mean(data_copy.astype(np.float32)**2))
                    # Scale to 0-100 range (32768 is max for int16)
                    level[0] = min(100, int(rms / 328 * 100))
                
                # Convert to mono 16kHz for Whisper
                mono_16k = resample_to_mono_16k(data_copy, sample_rate, channels)
                frame_queue.put(mono_16k)
            
            frame_queue.put(None)
            ts_thread.join()
            tl_thread.join()
            
    except Exception as e:
        if error is not None:
            error[0] = str(e)
    finally:
        ready[0] = None
