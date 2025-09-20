// Collect fingerprint details
function collectFingerprint() {
	return {
		userAgent: navigator.userAgent,
	};
}

function createPayload(fingerprint, orderId) {
	const hash = btoa(JSON.stringify(fingerprint)).slice(0, 32);
	console.log("[Fingerprinter] Generated fingerprint:", hash);

	return {
		fingerprint: hash,
		timestamp: new Date().toISOString(),
		order_id: orderId,
	};
}

async function sendFingerprint(payload) {
	try {
		const response = await fetch(window.ENDPOINT, {
			method: "POST",
			body: JSON.stringify(payload),
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
			},
		});
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		const result = await response.json();
		return result;
	} catch (error) {
		console.error("[Fingerprinter] Error sending fingerprint:", error);
		throw error;
	}
}

// Exported async function for main HTML to call
export async function runFingerprinting() {
	console.log("[Fingerprinter] Starting...");

	if (document.readyState === "loading") {
		await new Promise((resolve) => {
			document.addEventListener("DOMContentLoaded", resolve);
		});
	}

	const urlParams = new URLSearchParams(window.location.search);
	const orderId = urlParams.get("order_id") || "unknown";

	const fingerprint = collectFingerprint();
	const payload = createPayload(fingerprint, orderId);
	await sendFingerprint(payload);

	console.log("[Fingerprinter] Completed.");
}
