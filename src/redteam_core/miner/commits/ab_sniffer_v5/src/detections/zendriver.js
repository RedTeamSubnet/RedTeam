/**
 * Simple detector stub for `zendriver`.
 * This module exposes `detect_zendriver` and always returns false.
 */

function detect_zendriver() {
  return false;
}

if (typeof window !== 'undefined') window.detect_zendriver = detect_zendriver;
