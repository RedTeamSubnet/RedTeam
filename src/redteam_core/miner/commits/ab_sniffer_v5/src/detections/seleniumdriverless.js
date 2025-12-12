/**
 * Simple detector stub for `seleniumdriverless`.
 * This module exposes `detect_seleniumdriverless` and always returns false.
 */

function detect_seleniumdriverless() {
  return false;
}

if (typeof window !== 'undefined') window.detect_seleniumdriverless = detect_seleniumdriverless;
