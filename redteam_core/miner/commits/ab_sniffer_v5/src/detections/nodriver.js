/**
 * Simple detector stub for `nodriver`.
 * This module exposes `detect_nodriver` and always returns false.
 */

function detect_nodriver() {
  return false;
}

if (typeof window !== 'undefined') window.detect_nodriver = detect_nodriver;
