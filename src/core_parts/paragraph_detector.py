import math

class ParagraphDetector:
    """
    Adaptive paragraph detection based on speech pause patterns.
    
    Uses statistical analysis of pause durations to detect "significant" pauses
    that likely indicate paragraph breaks, while also enforcing hard limits
    on paragraph length.
    
    Parameters:
        threshold_std: Number of standard deviations above mean for a "significant" pause (default: 1.5)
        min_pause: Minimum pause duration to consider as potential break (default: 0.8s)
        max_chars: Maximum characters per paragraph before forced break (default: 500)
        max_words: Maximum words per paragraph before forced break (default: 100)
        window_size: Number of recent pauses to use for statistics (default: 30)
        warmup_count: Minimum pauses needed before adaptive mode (default: 5)
        warmup_threshold: Fixed threshold during warmup period (default: 2.0s)
    """
    
    def __init__(
        self,
        threshold_std=1.5,
        min_pause=0.8,
        max_chars=500,
        max_words=100,
        window_size=30,
        warmup_count=5,
        warmup_threshold=2.0
    ):
        self.threshold_std = threshold_std
        self.min_pause = min_pause
        self.max_chars = max_chars
        self.max_words = max_words
        self.window_size = window_size
        self.warmup_count = warmup_count
        self.warmup_threshold = warmup_threshold
        
        # State
        self.pause_history = []
        self.current_para_chars = 0
        self.current_para_words = 0
        self.last_absolute_end = None  # Track absolute end time across batches
    
    def _add_pause(self, duration):
        """Record a pause duration for statistics."""
        if duration > 0:  # Only track actual pauses
            self.pause_history.append(duration)
            if len(self.pause_history) > self.window_size:
                self.pause_history.pop(0)
    
    def _get_adaptive_threshold(self):
        """Calculate the current adaptive threshold based on pause history."""
        if len(self.pause_history) < self.warmup_count:
            return self.warmup_threshold
        
        n = len(self.pause_history)
        mean = sum(self.pause_history) / n
        variance = sum((p - mean) ** 2 for p in self.pause_history) / n
        std = math.sqrt(variance) if variance > 0 else 0
        
        # Threshold is mean + (threshold_std * std), but at least min_pause
        threshold = mean + (self.threshold_std * std)
        return max(threshold, self.min_pause)
    
    def _reset_paragraph(self):
        """Reset paragraph counters."""
        self.current_para_chars = 0
        self.current_para_words = 0
    
    def process_segments(self, segments, time_offset=0.0):
        """
        Process a list of Whisper segments and return text with paragraph breaks.
        
        Args:
            segments: List of Whisper segment objects with .text, .start, .end
            time_offset: Cumulative audio offset to convert relative to absolute timestamps
            
        Returns:
            String with paragraph breaks (\\n\\n) inserted where appropriate
        """
        if not segments:
            return ""
        
        result_parts = []
        
        for segment in segments:
            text = segment.text
            should_break = False
            
            # Convert to absolute timestamps
            absolute_start = segment.start + time_offset
            absolute_end = segment.end + time_offset
            
            # Check hard limits first
            new_chars = self.current_para_chars + len(text)
            new_words = self.current_para_words + len(text.split())
            if self.current_para_chars > 0:
                if new_chars > self.max_chars or new_words > self.max_words:
                    should_break = True
            
            # Check pause using absolute timestamps (works across batches!)
            if not should_break and self.last_absolute_end is not None:
                pause_duration = absolute_start - self.last_absolute_end
                if pause_duration > 0:
                    self._add_pause(pause_duration)
                    if pause_duration >= self.min_pause:
                        threshold = self._get_adaptive_threshold()
                        if pause_duration > threshold:
                            should_break = True
            
            # Apply break
            if should_break:
                result_parts.append("\n\n")
                self._reset_paragraph()
            
            # Add text and update counters
            result_parts.append(text)
            self.current_para_chars += len(text)
            self.current_para_words += len(text.split())
            
            # Track absolute end time for next comparison
            self.last_absolute_end = absolute_end
        
        return "".join(result_parts)
    
    def get_stats(self):
        """Return current statistics for debugging/display."""
        if len(self.pause_history) < 2:
            return {
                "pause_count": len(self.pause_history),
                "mean": None,
                "std": None,
                "threshold": self.warmup_threshold,
                "mode": "warmup"
            }
        
        n = len(self.pause_history)
        mean = sum(self.pause_history) / n
        variance = sum((p - mean) ** 2 for p in self.pause_history) / n
        std = math.sqrt(variance) if variance > 0 else 0
        
        return {
            "pause_count": n,
            "mean": round(mean, 3),
            "std": round(std, 3),
            "threshold": round(self._get_adaptive_threshold(), 3),
            "mode": "adaptive" if n >= self.warmup_count else "warmup"
        }
