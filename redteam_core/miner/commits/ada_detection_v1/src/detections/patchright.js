/**
 * Simple detector stub for `patchright`.
 * This module exposes `detect_patchright` and always returns false.
 */

function detect_patchright() {
  return false;
}

if (typeof window !== 'undefined') window.detect_patchright = detect_patchright;
