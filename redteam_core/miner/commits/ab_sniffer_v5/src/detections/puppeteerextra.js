/**
 * Simple detector stub for `puppeteerextra`.
 * This module exposes `detect_puppeteerextra` and always returns false.
 */

function detect_puppeteerextra() {
  return false;
}

if (typeof window !== 'undefined') window.detect_puppeteerextra = detect_puppeteerextra;
