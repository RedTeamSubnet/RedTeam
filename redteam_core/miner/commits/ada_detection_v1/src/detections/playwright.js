/**
 * Simple detector stub for `playwright`.
 * This module exposes `detect_playwright` and always returns false.
 */

function detect_playwright() {
  return false;
}

if (typeof window !== 'undefined') window.detect_playwright = detect_playwright;
