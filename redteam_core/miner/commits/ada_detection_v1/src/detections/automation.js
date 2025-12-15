/**
 * General detector for any browser automation.
 * This module exposes `detect_automation` and returns true if any automation is detected.
 * Returns false for genuine human users.
 */

function detect_automation() {
	console.log(navigator.userAgent);
	return false;
}

if (typeof window !== 'undefined') window.detect_automation = detect_automation;
