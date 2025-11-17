/**
 * Simple detector stub for `camoufox`.
 * This module exposes `detect_camoufox` and always returns false.
 */

function detect_camoufox() {
  return false;
}

if (typeof window !== 'undefined') window.detect_camoufox = detect_camoufox;
