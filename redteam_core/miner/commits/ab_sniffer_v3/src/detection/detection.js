// ==============================
// Data Repository
// ==============================
class DataRepository {
	#fingerprint = {};
	#mouse = [];
	#clicks = [];

	get fingerprint() {
		return this.#fingerprint;
	}
	set fingerprint(obj) {
		if (obj && typeof obj === "object") {
			this.#fingerprint = obj;
		} else {
			throw new TypeError("Fingerprint must be an object");
		}
	}

	get mouseEvents() {
		return this.#mouse;
	}
	set mouseEvents(events) {
		if (!Array.isArray(events)) throw new TypeError("Mouse events must be an array");
		this.#mouse = events;
	}

	get clickEvents() {
		return this.#clicks;
	}
	set clickEvents(events) {
		if (!Array.isArray(events)) throw new TypeError("Click events must be an array");
		this.#clicks = events;
	}

	addMouse(e) {
		this.#mouse.push(e);
	}
	addClick(e) {
		this.#clicks.push(e);
	}
	addFingerprint(key, val) {
		this.#fingerprint[key] = val;
	}
}

const repo = new DataRepository();

// ==============================
// Utility functions
// ==============================
const utils = {
	hash: (str) => {
		let out = 0;
		for (const ch of str) {
			out = (out << 5) - out + ch.charCodeAt(0);
			out |= 0;
		}
		return out >>> 0;
	},

	trackMouse: (e) => {
		console.log("mouse move", e);
		repo.addMouse({ x: e.clientX, y: e.clientY, time: e.timeStamp });
	},

	trackClick: (e) => {
		console.log("mouse click", e);
		repo.addClick({ x: e.clientX, y: e.clientY, time: e.timeStamp });
	}
};

document.addEventListener("mousemove", utils.trackMouse, true);
document.addEventListener("click", utils.trackClick, true);

// ==============================
// Fingerprinting helpers
// ==============================
const collectFingerPrint = () => {
	const testFont = (font, text, size, container) => {
		const span = document.createElement("span");
		span.style.fontFamily = font;
		span.style.fontSize = size;
		span.textContent = text;
		container.appendChild(span);
		const dims = { w: span.offsetWidth, h: span.offsetHeight };
		container.removeChild(span);
		return dims;
	};

	((skip = false) => {
		const canvas = document.createElement("canvas");
		const ctx = canvas.getContext("2d");
		let winding = false, geom, txt;

		const supported = !!(ctx && canvas.toDataURL);
		if (!supported) {
			geom = txt = "Unsupported";
		} else {
			ctx.rect(0, 0, 10, 10);
			ctx.rect(2, 2, 6, 6);
			winding = !ctx.isPointInPath(5, 5, "evenodd");

			if (skip) {
				geom = txt = "Skipped";
			} else {
				// Render text
				canvas.width = 240;
				canvas.height = 60;
				ctx.textBaseline = "alphabetic";
				ctx.fillStyle = "#f60";
				ctx.fillRect(100, 1, 62, 20);
				ctx.fillStyle = "#069";
				ctx.font = '11pt "Times New Roman"';
				const msg = `Cwm fjordbank gly ${String.fromCharCode(55357, 56835)}`;
				ctx.fillText(msg, 2, 15);
				ctx.fillStyle = "rgba(102,204,0,0.2)";
				ctx.font = "18pt Arial";
				ctx.fillText(msg, 4, 45);

				const t1 = canvas.toDataURL();
				const t2 = canvas.toDataURL();
				if (t1 !== t2) {
					geom = txt = "Unstable";
				} else {
					geom = t1;
					txt = t2;
				}
			}
		}

		repo.addFingerprint("unstableCanvas", {
			winding,
			geometry: utils.hash(geom),
			text: utils.hash(txt)
		});
	})();

	(() => {
		const text = "kkkkkkkkkkkkkmmmmmmmmmmlli";
		const size = "72px";
		const body = document.body;

		const rect = testFont("Arial", text, size, body);
		repo.addFingerprint("fontMetrics", { Arial: { boundingHeight: rect.h } });
	})();

	(() => {
		const fonts = ["Arial", "Verdana", "Helvetica", "Times New Roman", "Courier New", "Georgia", "Palatino"];
		const baseFonts = ["monospace", "sans-serif", "serif"];
		const sample = "kkkkkkkkkkkkkmmmmmmmmmmlli";
		const px = "72px";
		const body = document.body;

		const baseSizes = baseFonts.reduce((acc, f) => {
			acc[f] = testFont(f, sample, px, body);
			return acc;
		}, {});

		const found = fonts.filter(f => {
			const dims = testFont(f, sample, px, body);
			return !baseFonts.some(bf => dims.w === baseSizes[bf].w && dims.h === baseSizes[bf].h);
		});

		repo.addFingerprint("fontList", found);
	})();

	(() => {
		try {
			const gl = document.createElement("canvas").getContext("webgl");
			repo.addFingerprint("webglVendor", gl?.getParameter(gl.VENDOR) || null);
		} catch {
			repo.addFingerprint("webglVendor", null);
		}
	})();

	(() => {
		repo.addFingerprint("browserAPIs", {
			doNotTrack: navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack,
			pushNotification: "PushManager" in window
		});
	})();

	(() => {
		let min = matchMedia("(min-monochrome: 0)").matches ? 0 : -1;
		let max = min;

		if (min === 0) {
			for (let i = 0; i < 1000; i++) {
				if (!matchMedia(`(max-monochrome: ${i})`).matches) {
					max = i - 1;
					break;
				}
			}
		}
		repo.addFingerprint("monochromeDepth", { min, max });
	})();

	(() => {
		repo.addFingerprint("platform", navigator.platform);
		repo.addFingerprint("languages", navigator.languages);
	});

}

// ==============================
// Driver Detection
// ==============================
const setDriver = (d) => {
	try {
		localStorage.setItem("driver", d);
	} catch { }
	console.log("Detected driver type:", d);
};

const detectDriver = () => {
	const scoreDrivers = () => {
		const drivers = ["nodriver", "selenium", "seleniumbase", "patchright", "puppeteerextra", "zendriver", "camoufox"];
		const scores = Object.fromEntries(drivers.map(d => [d, 0]));
		const fp = repo.fingerprint;

		if (fp.unstableCanvas?.geometry === "4277458301" && fp.unstableCanvas?.text === "4229964566") {
			scores.camoufox++;
			return scores;
		}

		if (fp.platform.includes("Linux")) {
			["seleniumbase", "zendriver", "patchright", "nodriver", "selenium"].forEach(d => scores[d]++);
		} else if (fp.platform.includes("MacIntel")) {
			setDriver("camoufox");
			return 0;
		} else {
			scores.camoufox++;
			scores.puppeteerextra++;
		}

		if (!fp.languages.includes("en")) scores.patchright++;
		if (fp.fontList.length === 0) return setDriver("seleniumbase"), 0;
		if (fp.fontList.length > 1) return setDriver("camoufox"), 0;
		if (fp.webglVendor === "Mozilla") return setDriver("camoufox"), 0;
		if (!fp.browserAPIs.pushNotification) return setDriver("camoufox"), 0;
		if (fp.browserAPIs.doNotTrack) return setDriver("camoufox"), 0;
		if (fp.fontMetrics.Arial.boundingHeight > 80) return setDriver("camoufox"), 0;

		return scores;
	};
	const scores = scoreDrivers();
	if (scores === 0) return;

	const best = Object.entries(scores).reduce(
		(max, [drv, val]) => (val > max[1] ? [drv, val] : max),
		["", -1]
	)[0];

	if (["nodriver", "seleniumdriverless", "zendriver"].includes(best)) {
		if (repo.mouseEvents.length > 10) return setDriver("seleniumdriverless");
		if (repo.clickEvents[0]?.time < 1050) return setDriver("nodriver");
		return setDriver("zendriver");
	}
	setDriver(best);
	return best;
};

// ==============================
// Main Orchestrator
// ==============================
const runDetection = () => {
	collectFingerPrint();
	detectDriver();
};

// ==============================
// Form submission
// ==============================
document.addEventListener("submit", (e) => {
	try {
		runDetection();
	} catch {
		setDriver("nodriver");
	}
}, true);
