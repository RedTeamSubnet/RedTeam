/**
 * Simple detector stub for `pydoll`.
 * This module exposes `detect_pydoll` and always returns false.
 */

function detect_pydoll() {
  return false;
}

if (typeof window !== 'undefined') window.detect_pydoll = detect_pydoll;
