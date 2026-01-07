import time
from datetime import datetime, timedelta

class MinuteWindowTracker:
    def __init__(self, max_attempts=4):
        self.max_attempts = max_attempts
        self.attempts = 0
        self.window_start = None

    def record_attempt(self):
        now = datetime.now()
        if self.window_start is None:
            # first attempt in a new window
            self.window_start = now
            self.attempts = 1
            return True
        else:
            # check how much time has passed
            if now < self.window_start + timedelta(minutes=1):
                # still inside the same minute window
                self.attempts += 1
                if self.attempts <= self.max_attempts:
                    return True
                else:
                    # reached max attempts — wait until end of minute
                    self._wait_until_end_of_window()
                    # reset window for next minute
                    self.window_start = None
                    self.attempts = 0
                    # after waiting you can record this attempt as first of new window
                    self.window_start = datetime.now()
                    self.attempts = 1
                    return True
            else:
                # window has expired -> start new window
                self.window_start = now
                self.attempts = 1
                return True

    def _wait_until_end_of_window(self):
        now = datetime.now()
        window_end = self.window_start + timedelta(minutes=1)
        wait_secs = (window_end - now).total_seconds()
        if wait_secs > 0:
            print(f"Reached the max attempts ({self.max_attempts}) in the minute window; waiting {wait_secs:.2f} seconds until end of minute.")
            time.sleep(wait_secs)
