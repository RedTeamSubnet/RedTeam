/**
 * Simple detector stub for `seleniumbase`.
 * This module exposes `detect_seleniumbase` and always returns false.
 */

function detect_seleniumbase() {
  return false;
}

if (typeof window !== 'undefined') window.detect_seleniumbase = detect_seleniumbase;
