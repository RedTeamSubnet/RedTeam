// ===============================
// Fingerprinter + IP/VPN Checks
// ===============================

// ---------- WebGL ----------
function getWebGLInfo() {
	try {
		const canvas = document.createElement("canvas");
		const gl =
			canvas.getContext("webgl") ||
			canvas.getContext("experimental-webgl");
		if (!gl) return { webglSupported: false };
		const dbg = gl.getExtension("WEBGL_debug_renderer_info");
		const vendor = dbg
			? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)
			: gl.getParameter(gl.VENDOR);
		const renderer = dbg
			? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)
			: gl.getParameter(gl.RENDERER);
		const shading = gl.getParameter(gl.SHADING_LANGUAGE_VERSION);
		const version = gl.getParameter(gl.VERSION);
		const params = {
			aliasedLineWidthRange: gl.getParameter(gl.ALIASED_LINE_WIDTH_RANGE),
			aliasedPointSizeRange: gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE),
			maxCombinedTextureImageUnits: gl.getParameter(
				gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS
			),
			maxCubeMapTextureSize: gl.getParameter(
				gl.MAX_CUBE_MAP_TEXTURE_SIZE
			),
			maxFragmentUniformVectors: gl.getParameter(
				gl.MAX_FRAGMENT_UNIFORM_VECTORS
			),
			maxRenderbufferSize: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
			maxTextureImageUnits: gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS),
			maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
			maxVaryingVectors: gl.getParameter(gl.MAX_VARYING_VECTORS),
			maxVertexAttribs: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
			maxVertexTextureImageUnits: gl.getParameter(
				gl.MAX_VERTEX_TEXTURE_IMAGE_UNITS
			),
			maxVertexUniformVectors: gl.getParameter(
				gl.MAX_VERTEX_UNIFORM_VECTORS
			),
			stencilBits: gl.getParameter(gl.STENCIL_BITS),
			depthBits: gl.getParameter(gl.DEPTH_BITS),
			antialias: gl.getContextAttributes()?.antialias ?? null,
		};
		return {
			webglSupported: true,
			vendor,
			renderer,
			shading,
			version,
			params,
			driverType: (renderer || "")
				.toLowerCase()
				.match(/swiftshader|llvmpipe|mesa/)
				? "software"
				: "hardware",
		};
	} catch {
		return { webglSupported: false };
	}
}

// ---------- System ----------
function getSystemInfo() {
	const n = navigator;
	const ua = n.userAgent || "";
	const uaData = n.userAgentData
		? {
				brands:
					n.userAgentData.brands?.map(
						(b) => `${b.brand}:${b.version}`
					) ?? null,
				mobile: n.userAgentData.mobile ?? null,
				platform: n.userAgentData.platform ?? null,
		  }
		: null;

	const platform = n.platform || null;
	const lang = n.language || null;
	const languages = n.languages || null;
	const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || null;
	const hardwareConcurrency = n.hardwareConcurrency ?? null;
	const deviceMemory = n.deviceMemory ?? null;
	const maxTouchPoints = n.maxTouchPoints ?? 0;

	const screenInfo = {
		width: screen.width,
		height: screen.height,
		availWidth: screen.availWidth,
		availHeight: screen.availHeight,
		colorDepth: screen.colorDepth,
		pixelDepth: screen.pixelDepth,
		devicePixelRatio: window.devicePixelRatio,
	};

	return {
		ua,
		uaData,
		platform,
		lang,
		languages,
		timeZone,
		hardwareConcurrency,
		deviceMemory,
		maxTouchPoints,
		screen: screenInfo,
	};
}

function hashStringFast(str) {
	let h = 2166136261 >>> 0;
	for (let i = 0; i < str.length; i++) {
		h ^= str.charCodeAt(i);
		h = Math.imul(h, 16777619);
	}
	return (h >>> 0).toString(16);
}

// ---------- Technical ----------
function canvasFingerprint() {
	try {
		const c = document.createElement("canvas");
		c.width = 256;
		c.height = 128;
		const ctx = c.getContext("2d");
		ctx.textBaseline = "alphabetic";
		ctx.fillStyle = "#f60";
		ctx.fillRect(125, 1, 62, 20);
		ctx.fillStyle = "#069";
		ctx.font = '16pt "Times New Roman"';
		ctx.fillText("canvas-fp-🙂", 2, 32);
		ctx.strokeStyle = "#ff0";
		ctx.arc(110, 60, 50, 0, Math.PI * 2);
		ctx.stroke();
		const data = c.toDataURL();
		return { hash: hashStringFast(data), dataLen: data.length };
	} catch {
		return { hash: null, dataLen: 0 };
	}
}

async function audioFingerprint() {
	try {
		const ctx = new (window.AudioContext || window.webkitAudioContext)();
		const osc = ctx.createOscillator();
		const comp = ctx.createDynamicsCompressor();
		return await new Promise((resolve) => {
			osc.type = "triangle";
			osc.frequency.value = 10000;
			osc.connect(comp);
			comp.connect(ctx.destination);
			osc.start(0);
			setTimeout(async () => {
				osc.stop();
				const fp = `${ctx.sampleRate}|${comp.threshold?.value ?? ""},${
					comp.knee?.value ?? ""
				},${comp.ratio?.value ?? ""},${comp.attack?.value ?? ""},${
					comp.release?.value ?? ""
				}`;
				try {
					await ctx.close();
				} catch {}
				resolve(hashStringFast(fp));
			}, 150);
		});
	} catch {
		return null;
	}
}

function getTechnicalInfoSync() {
	const n = navigator;
	const media = {
		mediaDevices: !!navigator.mediaDevices,
		getUserMedia: !!(
			navigator.mediaDevices && navigator.mediaDevices.getUserMedia
		),
	};
	const codecs = {
		h264: !!document
			.createElement("video")
			.canPlayType('video/mp4; codecs="avc1.42E01E"'),
		h265: !!document
			.createElement("video")
			.canPlayType('video/mp4; codecs="hev1"'),
		vp9: !!document
			.createElement("video")
			.canPlayType('video/webm; codecs="vp9"'),
		av1: !!document
			.createElement("video")
			.canPlayType('video/mp4; codecs="av01.0.05M.08"'),
		opus: !!document
			.createElement("audio")
			.canPlayType('audio/ogg; codecs="opus"'),
		aac: !!document
			.createElement("audio")
			.canPlayType('audio/mp4; codecs="mp4a.40.2"'),
	};
	const conn = n.connection
		? {
				downlink: n.connection.downlink,
				effectiveType: n.connection.effectiveType,
				rtt: n.connection.rtt,
				saveData: n.connection.saveData,
		  }
		: null;
	const clipboard = !!navigator.clipboard;
	const storage = {
		localStorage: (function () {
			try {
				const k = "__t";
				localStorage.setItem(k, "1");
				localStorage.removeItem(k);
				return true;
			} catch {
				return false;
			}
		})(),
		sessionStorage: (function () {
			try {
				const k = "__t";
				sessionStorage.setItem(k, "1");
				sessionStorage.removeItem(k);
				return true;
			} catch {
				return false;
			}
		})(),
		indexedDB: !!window.indexedDB,
	};
	const perf = {
		navTiming: !!(performance && performance.timing),
		memory:
			performance && "memory" in performance
				? {
						jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
						totalJSHeapSize: performance.memory.totalJSHeapSize,
						usedJSHeapSize: performance.memory.usedJSHeapSize,
				  }
				: null,
	};
	const canvas = canvasFingerprint();
	return { media, codecs, conn, clipboard, storage, perf, canvas };
}

// ---------- Utilities ----------
function keyExists(obj, keyPattern) {
	try {
		return Object.keys(obj).some((k) => keyPattern.test(k));
	} catch {
		return false;
	}
}
function isFirefoxUA(ua) {
	return /\bFirefox\/\d+/.test(ua) && !/Seamonkey/i.test(ua);
}

// ---------- Bot / automation detection ----------
async function detectBotType() {
	const n = navigator;
	const ua = n.userAgent || "";
	const brands = n.userAgentData?.brands?.map((b) => b.brand) || [];
	const matchedSignals = [];
	const details = { hard: {}, medium: {}, soft: {} };

	const hard = {
		webdriver: !!n.webdriver,
		headlessChromeUA: /\bHeadlessChrome\b/i.test(ua),
		headlessFirefoxUA: /\bHeadlessFirefox\b/i.test(ua),

		// Puppeteer
		pptrCdcGlobal: keyExists(window, /^cdc_[a-z0-9_]+$/i),
		puppeteerStealthHints: !!(
			window.chrome?.app &&
			window.chrome?.webstore === undefined &&
			!("sharedArrayBuffer" in window) &&
			/Chrome/i.test(ua)
		),

		// Playwright
		playwrightGlobal: !!(
			window.__pwUnwrap ||
			window.playwright ||
			window.__pwEnv
		),

		// Cypress
		cypressGlobal: !!window.Cypress,

		// Selenium (Chrome)
		seleniumChromeArtifacts: !!(
			window.__webdriver_script_fn ||
			window.__driver_evaluate ||
			window.__webdriver_evaluate
		),

		// Selenium / GeckoDriver (Firefox)
		geckoDriverWebdriver: !!n.webdriver && isFirefoxUA(ua),
		mozAutomation: !!n.mozAutomation,

		// Others
		wdioGlobal: !!(window.__wdio || window.wdio),
		testcafeGlobal: !!(
			window["%testCafeAutomation%"] || window["%hammerhead%"]
		),
		protractorGlobal: !!(window.protractor || window.__TESTABILITY__),
		nightmareGlobal: !!window.__nightmare,
		phantomGlobal: !!(window.callPhantom || window._phantom),
		electronEnv:
			!!window.process?.versions?.electron || /\bElectron\b/i.test(ua),
		nwjsEnv: !!window.process?.versions?.nw,

		// Camoufox (if UA exposes it)
		camoufoxUA: /\bCamoufox\b/i.test(ua),
	};
	for (const [k, v] of Object.entries(hard)) {
		details.hard[k] = !!v;
		if (v) matchedSignals.push(k);
	}

	const medium = {
		webglSoftwareRenderer: (() => {
			try {
				const c = document.createElement("canvas");
				const gl =
					c.getContext("webgl") || c.getContext("experimental-webgl");
				if (!gl) return false;
				const dbg = gl.getExtension("WEBGL_debug_renderer_info");
				const renderer = dbg
					? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)
					: gl.getParameter(gl.RENDERER);
				return /swiftshader|llvmpipe|mesa|software/i.test(
					renderer || ""
				);
			} catch {
				return false;
			}
		})(),
		noPlugins: (function () {
			try {
				return (navigator.plugins?.length ?? 0) === 0;
			} catch {
				return false;
			}
		})(),
		emptyLanguages: !Array.isArray(n.languages) || n.languages.length === 0,
		oddBrands:
			brands.length && brands.some((b) => /Not.?A.?Brand/i.test(b)),
		notificationsDenied: null,
	};
	try {
		if (navigator.permissions?.query) {
			const st = await navigator.permissions.query({
				name: "notifications",
			});
			medium.notificationsDenied = st?.state === "denied";
		}
	} catch {}
	for (const [k, v] of Object.entries(medium)) {
		details.medium[k] = !!v;
		if (v) matchedSignals.push(k);
	}

	const soft = {
		firefoxLikeAndWeird: (function () {
			const isFF = isFirefoxUA(ua);
			const hasInstallTrigger =
				typeof window.InstallTrigger !== "undefined";
			const hasSidebar = typeof window.sidebar !== "undefined";
			return isFF && (!hasInstallTrigger || !hasSidebar);
		})(),
	};
	for (const [k, v] of Object.entries(soft)) {
		details.soft[k] = !!v;
		if (v) matchedSignals.push(k);
	}

	// scoring
	let score = 0;
	const w = (c, n) => {
		if (c) score += n;
	};

	w(hard.webdriver, 4);
	w(hard.headlessChromeUA, 4);
	w(hard.headlessFirefoxUA, 4);
	w(hard.pptrCdcGlobal, 4);
	w(hard.puppeteerStealthHints, 2);
	w(hard.playwrightGlobal, 4);
	w(hard.cypressGlobal, 4);
	w(hard.seleniumChromeArtifacts, 3);
	w(hard.geckoDriverWebdriver, 4);
	w(hard.mozAutomation, 4);
	w(hard.wdioGlobal, 3);
	w(hard.testcafeGlobal, 4);
	w(hard.protractorGlobal, 2);
	w(hard.nightmareGlobal, 2);
	w(hard.phantomGlobal, 3);
	w(hard.electronEnv, 2);
	w(hard.nwjsEnv, 2);
	w(hard.camoufoxUA, 5);

	w(medium.webglSoftwareRenderer, 1);
	w(medium.noPlugins, 1);
	w(medium.emptyLanguages, 1);
	w(medium.oddBrands, 1);
	w(medium.notificationsDenied, 1);

	w(soft.firefoxLikeAndWeird, 1);

	// labeling
	let label = "human_or_unknown";
	const precedence = [
		[
			"camoufox",
			hard.camoufoxUA ||
				(isFirefoxUA(ua) &&
					(hard.mozAutomation || hard.geckoDriverWebdriver)),
		],
		["cypress", hard.cypressGlobal],
		["playwright", hard.playwrightGlobal],
		[
			"puppeteer_or_headless_chrome",
			hard.pptrCdcGlobal ||
				hard.headlessChromeUA ||
				hard.puppeteerStealthHints,
		],
		["selenium_gecko", hard.mozAutomation || hard.geckoDriverWebdriver],
		[
			"selenium_webdriver",
			hard.seleniumChromeArtifacts ||
				(hard.webdriver && !isFirefoxUA(ua)),
		],
		["webdriverio", hard.wdioGlobal],
		["testcafe", hard.testcafeGlobal],
		["protractor", hard.protractorGlobal],
		["nightmare", hard.nightmareGlobal],
		["phantomjs", hard.phantomGlobal],
		["electron", hard.electronEnv],
		["nwjs", hard.nwjsEnv],
	];
	for (const [name, cond] of precedence) {
		if (cond) {
			label = name;
			break;
		}
	}
	if (label === "human_or_unknown") {
		if (score >= 6) label = "likely_automation";
		else if (score >= 3) label = "suspected_automation";
	}

	const confidence = Math.max(0, Math.min(1, score / 10));
	return { label, confidence, score, matchedSignals, details };
}

// ---------- NEW: helpers for IP fetching ----------
async function fetchJSON(url, { timeoutMs = 2500, headers } = {}) {
	const ac = new AbortController();
	const t = setTimeout(() => ac.abort(), timeoutMs);
	try {
		const res = await fetch(url, { headers, signal: ac.signal });
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		return await res.json();
	} finally {
		clearTimeout(t);
	}
}

// ---------- NEW: Public IP / Geo / ASN (with fallbacks) ----------
async function getPublicIPInfo() {
	const providers = [
		// Minimal IP only
		async () => {
			const d = await fetchJSON("https://api.ipify.org?format=json");
			return { ip: d.ip || null };
		},
		// ipapi.co: ASN/org/loc/tz, no token needed
		async () => {
			const d = await fetchJSON("https://ipapi.co/json/");
			return {
				ip: d.ip ?? null,
				country: d.country ?? null,
				region: d.region ?? null,
				city: d.city ?? null,
				latitude: d.latitude ?? null,
				longitude: d.longitude ?? null,
				timezone: d.timezone ?? null,
				asn: d.asn ?? null,
				org: d.org ?? null,
			};
		},
		// ipinfo.io: basic without token; parses "AS123 Org"
		async () => {
			const d = await fetchJSON("https://ipinfo.io/json");
			const org = d.org || null;
			let asn = null,
				asOrg = null;
			if (org) {
				const m = org.match(/^AS(\d+)\s+(.+)$/i);
				if (m) {
					asn = `AS${m[1]}`;
					asOrg = m[2];
				}
			}
			return {
				ip: d.ip ?? null,
				country: d.country ?? null,
				region: d.region ?? null,
				city: d.city ?? null,
				timezone: d.timezone ?? null,
				asn: asn,
				org: asOrg || org,
				privacy: d.privacy ?? null, // may be undefined without token
			};
		},
	];

	let best = null,
		errors = [];
	for (const p of providers) {
		try {
			const out = await p();
			if (out && out.ip) {
				best = out;
				break;
			}
		} catch (e) {
			errors.push(String(e));
		}
	}

	return {
		ok: !!best,
		data: best || null,
		error: best
			? null
			: errors[errors.length - 1] || "No provider succeeded",
	};
}

// ---------- NEW: WebRTC ICE hints (srflx/relay) ----------
async function getWebRTCIPHints() {
	try {
		const RTCPeer =
			window.RTCPeerConnection || window.webkitRTCPeerConnection;
		if (!RTCPeer) return { supported: false, candidateTypes: [], ips: [] };

		const pc = new RTCPeerConnection({
			iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
		});
		const candidateTypes = new Set();
		const ips = new Set();

		pc.createDataChannel("x"); // start ICE
		const offer = await pc.createOffer({ iceRestart: true });
		await pc.setLocalDescription(offer);

		await new Promise((resolve) => {
			const timer = setTimeout(() => {
				try {
					pc.close();
				} catch {}
				resolve();
			}, 1500);
			pc.onicecandidate = (evt) => {
				if (!evt || !evt.candidate) return;
				const c = evt.candidate.candidate || "";
				const typMatch = c.match(/\btyp\s+(\w+)/i);
				if (typMatch) candidateTypes.add(typMatch[1].toLowerCase());
				const ipMatch = c.match(
					/(?:\d{1,3}\.){3}\d{1,3}|[a-f0-9:]{2,}/i
				);
				if (ipMatch) ips.add(ipMatch[0]);
			};
			pc.onicegatheringstatechange = () => {
				if (pc.iceGatheringState === "complete") {
					clearTimeout(timer);
					try {
						pc.close();
					} catch {}
					resolve();
				}
			};
		});

		return {
			supported: true,
			candidateTypes: Array.from(candidateTypes),
			ips: Array.from(ips),
		};
	} catch {
		return { supported: false, candidateTypes: [], ips: [] };
	}
}

// ---------- NEW: VPN/Proxy heuristic ----------
function isoLangToCountry(lang) {
	try {
		const p = lang?.split?.("-") || [];
		return p[p.length - 1]?.toUpperCase?.() || null;
	} catch {
		return null;
	}
}

function looksLikeHosting(asOrgOrOrg = "") {
	const s = (asOrgOrOrg || "").toLowerCase();
	return /amazon|aws|google|microsoft|azure|digitalocean|linode|akamai|cloudflare|ovh|hetzner|contabo|vultr|alibaba|hivelocity|ionos|upcloud|gigenet|leaseweb|kimsufi|scaleway|oracle cloud|packet|equinix/.test(
		s
	);
}

function assessProxyVpn(ipInfo, sys, webrtc) {
	const signals = [];
	const priv = ipInfo?.privacy || {};
	const ipTz = (ipInfo?.timezone || "").toLowerCase();
	const sysTz = (sys?.timeZone || "").toLowerCase();

	// Provider flags (if available)
	if (priv?.vpn) signals.push("provider_vpn");
	if (priv?.proxy) signals.push("provider_proxy");
	if (priv?.tor) signals.push("provider_tor");
	if (priv?.hosting) signals.push("provider_hosting");

	// Hosting/datacenter org
	if (looksLikeHosting(ipInfo?.org)) signals.push("asn_hosting_org");

	// Timezone mismatch
	if (ipTz && sysTz && !ipTz.includes(sysTz) && !sysTz.includes(ipTz)) {
		signals.push("timezone_mismatch");
	}

	// Language-country vs IP country (rough)
	const langCountry = isoLangToCountry(sys?.lang);
	if (langCountry && ipInfo?.country && langCountry !== ipInfo.country) {
		const langs = Array.isArray(sys?.languages) ? sys.languages : [];
		const hasIpCountryLang = langs.some(
			(l) => isoLangToCountry(l) === ipInfo.country
		);
		if (!hasIpCountryLang) signals.push("lang_vs_ip_country_mismatch");
	}

	// WebRTC relay-only (mild)
	const types = new Set(webrtc?.candidateTypes || []);
	if (
		webrtc?.supported &&
		types.size &&
		!types.has("host") &&
		!types.has("srflx")
	) {
		signals.push("webrtc_relay_only");
	}

	// Score
	let score = 0;
	const add = (n) => (score += n);

	if (signals.includes("provider_vpn")) add(5);
	if (signals.includes("provider_proxy")) add(4);
	if (signals.includes("provider_tor")) add(6);
	if (signals.includes("provider_hosting")) add(3);
	if (signals.includes("asn_hosting_org")) add(2);
	if (signals.includes("timezone_mismatch")) add(1);
	if (signals.includes("lang_vs_ip_country_mismatch")) add(1);
	if (signals.includes("webrtc_relay_only")) add(1);

	let label = "none";
	if (score >= 6) label = "probable_vpn_or_proxy";
	else if (score >= 3) label = "suspected_vpn_or_proxy";

	const confidence = Math.max(0, Math.min(1, score / 8));
	return { label, confidence, score, signals };
}

// ---------- Collector ----------
async function collectFingerprint() {
	const [gl, sys] = [getWebGLInfo(), getSystemInfo()];
	const techSync = getTechnicalInfoSync();

	// Run network/bot/audio in parallel
	const [ipInfoRes, webrtcHints, audio, bot] = await Promise.all([
		getPublicIPInfo(),
		getWebRTCIPHints(),
		audioFingerprint(),
		detectBotType(),
	]);

	const ipInfo = ipInfoRes.ok ? ipInfoRes.data : null;
	const vpn = assessProxyVpn(ipInfo, sys, webrtcHints);

	const payload = {
		driver: { type: gl.driverType || null, webgl: gl },
		system: sys,
		technical: { ...techSync, audioHash: audio },
		network: {
			publicIP: ipInfo?.ip || null,
			geo: ipInfo
				? {
						country: ipInfo.country ?? null,
						region: ipInfo.region ?? null,
						city: ipInfo.city ?? null,
						timezone: ipInfo.timezone ?? null,
						latitude: ipInfo.latitude ?? null,
						longitude: ipInfo.longitude ?? null,
						asn: ipInfo.asn ?? null,
						org: ipInfo.org ?? null,
				  }
				: null,
			ipProviderHadError: ipInfoRes.ok
				? null
				: ipInfoRes.error || "unknown",
			webrtc: webrtcHints,
		},
		vpnProxy: vpn, // { label, confidence, score, signals }
		bot,
	};

	return payload;
}

async function hmacSha256Hex(keyBytes, message) {
	const key = await crypto.subtle.importKey(
		"raw",
		keyBytes,
		{ name: "HMAC", hash: "SHA-256" },
		false,
		["sign"]
	);
	const sig = await crypto.subtle.sign(
		"HMAC",
		key,
		new TextEncoder().encode(message)
	);
	return [...new Uint8Array(sig)]
		.map((b) => b.toString(16).padStart(2, "0"))
		.join("");
}

// ---------- Payload & Transport ----------
async function createPayload(fingerprint, orderId) {
	const hash = await hmacSha256Hex(
		new TextEncoder().encode("secret"),
		JSON.stringify(fingerprint)
	);
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

// ---------- Public API ----------
export async function runFingerprinting() {
	console.log("[Fingerprinter] Starting...");

	if (document.readyState === "loading") {
		await new Promise((resolve) => {
			document.addEventListener("DOMContentLoaded", resolve);
		});
	}

	const urlParams = new URLSearchParams(window.location.search);
	const orderId = urlParams.get("order_id") || "unknown";

	const fingerprint = await collectFingerprint();
	const payload = await createPayload(fingerprint, orderId);
	await sendFingerprint(payload);

	console.log("[Fingerprinter] Completed.");
}
