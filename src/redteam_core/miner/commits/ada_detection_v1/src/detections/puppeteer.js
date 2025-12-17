/**
 * Simple detector stub for `puppeteer`.
 * This module exposes `detect_puppeteer` and always returns false.
 */

function detect_puppeteer() {
  return false;
}

if (typeof window !== 'undefined') window.detect_puppeteer = detect_puppeteer;
