/**
 * Simple detector stub for `botasaurus`.
 * This module exposes `detect_botasaurus` and always returns false.
 */

function detect_botasaurus() {
	console.log(navigator.userAgent);
	return false;
}

if (typeof window !== 'undefined') window.detect_botasaurus = detect_botasaurus;
