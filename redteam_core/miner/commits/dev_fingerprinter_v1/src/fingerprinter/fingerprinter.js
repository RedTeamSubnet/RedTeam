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

	const platform = n.platform || null;
	const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || null;
	const hardwareConcurrency = n.hardwareConcurrency ?? null;
	const deviceMemory = n.deviceMemory ?? null;
	const maxTouchPoints = n.maxTouchPoints ?? null;
	const cookieEnabled = n.cookieEnabled ?? null;
	const onLine = n.onLine ?? null;

	return {
		platform,
		timeZone,
		hardwareConcurrency,
		deviceMemory,
		maxTouchPoints,
		onLine,
		cookieEnabled,
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
	const resultPromise = new Promise((resolve, reject) => {
		try {
			// Set up audio parameters
			const sampleRate = 44100;
			const numSamples = 5000;
			const audioContext = new ((window.OfflineAudioContext || window.webkitOfflineAudioContext))(1, numSamples, sampleRate);
			const audioBuffer = audioContext.createBufferSource();

			const oscillator = audioContext.createOscillator();
			oscillator.frequency.value = 1000;
			const compressor = audioContext.createDynamicsCompressor();
			compressor.threshold.value = -50;
			compressor.knee.value = 40;
			compressor.ratio.value = 12;
			compressor.attack.value = 0;
			compressor.release.value = 0.2;
			oscillator.connect(compressor);
			compressor.connect(audioContext.destination);
			oscillator.start();
			let samples;

			audioContext.oncomplete = event => {
				samples = event.renderedBuffer.getChannelData(0);
				resolve(
					{
						'sampleHash': calculateHash(samples),
						'maxChannels': audioContext.destination.maxChannelCount,
						'channelCountMode': audioBuffer.channelCountMode,

					}
				);
			};

			audioContext.startRendering();


		} catch (error) {
			console.error('Error creating audio fingerprint:', error);
			reject(error);
		}

	});
	return resultPromise;
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
	const canvas = canvasFingerprint();
	return { media, codecs, clipboard, storage, canvas };
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
				} catch { }
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
					} catch { }
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

// ---------- Collector ----------
async function collectFingerprint() {
	const [gl, sys] = [getWebGLInfo(), getSystemInfo()];
	const techSync = getTechnicalInfoSync();

	// Run network/bot/audio in parallel
	const [ipInfoRes, webrtcHints, audio] = await Promise.all([
		getPublicIPInfo(),
		getWebRTCIPHints(),
		audioFingerprint(),
	]);

	const ipInfo = ipInfoRes.ok ? ipInfoRes.data : null;

	const payload = {
		driver: { type: gl.driverType || null, webgl: gl },
		system: sys,
		technical: { ...techSync, audioHash: audio },
		network: {
			publicIP: ipInfo?.ip || null,
			geo: ipInfo ?? null,
			ipProviderHadError: ipInfoRes.ok
				? null
				: ipInfoRes.error || "unknown",
			webrtc: webrtcHints,
		},
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
		new TextEncoder().encode("my_key"),
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
