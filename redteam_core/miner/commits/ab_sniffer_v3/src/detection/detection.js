// Data collection system
class DataStore {
	constructor() {
		this._fingerprint = {};
		this._mouseEvents = [];
		this._clickEvents = [];
	}

	// Fingerprint
	get fingerprint() {
		return this._fingerprint;
	}

	set fingerprint(value) {
		if (typeof value === 'object' && value !== null) {
			this._fingerprint = value;
		} else {
			throw new Error("Fingerprint must be an object");
		}
	}

	// Mouse Events
	get mouseEvents() {
		return this._mouseEvents;
	}

	set mouseEvents(events) {
		if (Array.isArray(events)) {
			this._mouseEvents = events;
		} else {
			throw new Error("Mouse events must be an array");
		}
	}

	// Click Events
	get clickEvents() {
		return this._clickEvents;
	}

	set clickEvents(events) {
		if (Array.isArray(events)) {
			this._clickEvents = events;
		} else {
			throw new Error("Click events must be an array");
		}
	}

	// Utility methods
	addMouseEvent(event) {
		this._mouseEvents.push(event);
	}

	addClickEvent(event) {
		this._clickEvents.push(event);
	}

	addFingerprintData(key, value) {
		this._fingerprint[key] = value;
	}
}

const store = new DataStore();


// Hash function for data processing
const createHash = (input) => {
	let result = 0;
	for (let i = 0; i < input.length; i++) {
		const char = input.charCodeAt(i);
		result = (result << 5) - result + char;
		result |= 0;
	}
	return result >>> 0;
};

// Mouse movement tracking
const trackMouseMovement = (event) => {
	console.log(`mouse move ${event}`)
	store.addMouseEvent({
		x: event.clientX,
		y: event.clientY,
		time: event.timeStamp
	});
};

// Mouse click tracking
const trackMouseClick = (event) => {
	console.log(`mouse click ${event}`)
	store.addClickEvent({
		x: event.clientX,
		y: event.clientY,
		time: event.timeStamp
	});
};

document.addEventListener('mousemove', trackMouseMovement, true);
document.addEventListener('click', trackMouseClick, true);

// Collect system information
const collectSystemInfo = () => {
	store.addFingerprintData('platform', navigator.platform);
	store.addFingerprintData('languages', navigator.languages);
};

const analyzeFontRendering = () => {
	const testString = 'kkkkkkkkkkkkkmmmmmmmmmmlli';
	const testSize = '72px';
	const container = document.getElementsByTagName('body')[0];

	const element = document.createElement('span');
	element.style.fontSize = testSize;
	element.style.fontFamily = 'Arial';
	element.innerHTML = testString;
	container.appendChild(element);

	const rect = element.getBoundingClientRect();
	store.addFingerprintData('fontMetrics', {
		Arial: {
			boundingHeight: rect.height
		}
	});

	container.removeChild(element);
};

// Scan available fonts
const scanAvailableFonts = () => {
	const testString = 'kkkkkkkkkkkkkmmmmmmmmmmlli';
	const testSize = '72px';
	const container = document.getElementsByTagName('body')[0];

	const baseFonts = ['monospace', 'sans-serif', 'serif'];
	const fontList = ['Arial', 'Verdana', 'Helvetica', 'Times New Roman', 'Courier New', 'Georgia', 'Palatino'];

	const baseFontSizes = {};
	const fontSizes = {};

	// Measure base font dimensions
	baseFonts.forEach(font => {
		const element = document.createElement('span');
		element.style.fontSize = testSize;
		element.style.fontFamily = font;
		element.innerHTML = testString;
		container.appendChild(element);
		baseFontSizes[font] = { width: element.offsetWidth, height: element.offsetHeight };
		container.removeChild(element);
	});

	// Test specific fonts
	fontList.forEach(font => {
		const element = document.createElement('span');
		element.style.fontSize = testSize;
		element.style.fontFamily = font;
		element.innerHTML = testString;
		container.appendChild(element);
		fontSizes[font] = { width: element.offsetWidth, height: element.offsetHeight };
		container.removeChild(element);
	});

	// Detect available fonts
	const availableFonts = [];
	fontList.forEach(font => {
		let detected = false;
		baseFonts.forEach(baseFont => {
			if (fontSizes[font].width === baseFontSizes[baseFont].width &&
				fontSizes[font].height === baseFontSizes[baseFont].height) {
				detected = true;
			}
		});
		if (!detected) {
			availableFonts.push(font);
		}
	});

	store.addFingerprintData('fontList', availableFonts);
};

// Extract WebGL information
const extractWebGLInfo = () => {
	try {
		const canvas = document.createElement('canvas');
		const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
		store.addFingerprintData('webglVendor', gl ? gl.getParameter(gl.VENDOR) : null);
	} catch {
		store.addFingerprintData('webglVendor', null);
	}
};

// Detect browser capabilities
const detectBrowserCapabilities = () => {
	store.addFingerprintData('browserAPIs', {
		doNotTrack: navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack,
		pushNotification: 'PushManager' in window
	});
};

// Analyze monochrome depth
const analyzeMonochromeDepth = () => {
	store.addFingerprintData('monochromeDepth', window.screen.colorDepth);
	let min = matchMedia('(min-monochrome: 0)').matches
	min = min ? 0 : -1;
	let max = min;
	if (min == 0) {
		for (let i = 0; i < 1000; i++) {
			if (!matchMedia(`(max-monochrome: ${i})`).matches) {
				max = i - 1;
				break;
			}
		}
	}
	store.addFingerprintData('monochromeDepth', { min, max });
};

// Generate unstable canvas fingerprint
const generateUnstableCanvasFingerprint = (skipImages = false) => {
	const isSupported = (canvas, context) => !!(context && canvas.toDataURL)
	const doesSupportWinding = (context) => {
		context.rect(0, 0, 10, 10)
		context.rect(2, 2, 6, 6)
		return !context.isPointInPath(5, 5, 'evenodd')
	}
	const renderTextImage = (canvas, context) => {
		canvas.width = 240
		canvas.height = 60
		context.textBaseline = 'alphabetic'
		context.fillStyle = '#f60'
		context.fillRect(100, 1, 62, 20)
		context.fillStyle = '#069'
		context.font = '11pt "Times New Roman"'
		const printedText = `Cwm fjordbank gly ${String.fromCharCode(55357, 56835) /**/}`
		context.fillText(printedText, 2, 15)
		context.fillStyle = 'rgba(102, 204, 0, 0.2)'
		context.font = '18pt Arial'
		context.fillText(printedText, 4, 45)
	}
	const renderImages = (canvas, context) => {
		renderTextImage(canvas, context)
		const textImage1 = canvas.toDataURL()
		const textImage2 = canvas.toDataURL()
		if (textImage1 !== textImage2) {
			return ['Unstable', 'Unstable']
		}
		renderGeometryImage(canvas, context)
		const geometryImage = canvas.toDataURL()
		return [geometryImage, textImage1]
	}
	const renderGeometryImage = (canvas, context) => {
		canvas.width = 122
		canvas.height = 110
		context.globalCompositeOperation = 'multiply'
		for (const [color, x, y] of [
			['#f2f', 40, 40],
			['#2ff', 80, 40],
			['#ff2', 60, 80],
		]) {
			context.fillStyle = color
			context.beginPath()
			context.arc(x, y, 40, 0, Math.PI * 2, true)
			context.closePath()
			context.fill()
		}
		context.fillStyle = '#f9c'
		context.arc(60, 60, 60, 0, Math.PI * 2, true)
		context.arc(60, 60, 20, 0, Math.PI * 2, true)
		context.fill('evenodd')
	}
	let winding = false
	let geometry
	let text
	const c = document.createElement('canvas')
	c.width = 1
	c.height = 1
	const [canvas, context] = [c, c.getContext('2d')]
	if (!isSupported(canvas, context)) {
		geometry = text = 'Unsupported'
	} else {
		winding = doesSupportWinding(context)

		if (skipImages) {
			geometry = text = 'Skipped'
		} else {
			;[geometry, text] = renderImages(canvas, context)
		}
	}

	store.addFingerprintData('unstableCanvas', { winding, geometry: createHash(geometry), text: createHash(text) });
};

var calculateDriverScores = () => {
	const drivers = ["nodriver", "selenium", "seleniumbase", "patchright", "puppeteerextra", "zendriver", "camoufox"];
	const scores = {};

	// Initialize scores
	drivers.forEach(driver => {
		scores[driver] = 0;
	});

	if (store.fingerprint.unstableCanvas.geometry == "4277458301" && store.fingerprint.unstableCanvas.text == "4229964566") {
		scores.camoufox += 1;
		return scores;
	}

	// Platform-based scoring
	if (store.fingerprint.platform.includes("Linux")) {
		scores.seleniumbase += 1;
		scores.zendriver += 1;
		scores.patchright += 1;
		scores.nodriver += 1;
		scores.selenium += 1;
	} else if (store.fingerprint.platform.includes("MacIntel")) {
		setDriverResult("camoufox");
		return 0;
	} else {
		scores.camoufox += 1;
		scores.puppeteerextra += 1;
	}

	// Language-based scoring
	if (!store.fingerprint.languages.includes("en")) {
		scores.patchright += 1;
	}

	// Font-based scoring
	if (store.fingerprint.fontList.length === 0) {
		setDriverResult("seleniumbase");
		return 0;
	}

	if (store.fingerprint.fontList.length > 1) {
		setDriverResult("camoufox");
		return 0;
	}

	// WebGL-based scoring
	if (store.fingerprint.webglVendor === "Mozilla") {
		setDriverResult("camoufox");
		return 0;
	}

	// API-based scoring
	if (!store.fingerprint.browserAPIs.pushNotification) {
		setDriverResult("camoufox");
		return 0;
	}

	if (store.fingerprint.browserAPIs.doNotTrack) {
		setDriverResult("camoufox");
		return 0;
	}

	if (store.fingerprint.fontMetrics.Arial.boundingHeight > 80) {
		setDriverResult("camoufox");
		return 0;
	}

	return scores;
};

// Process driver detection
const processDriverDetection = () => {
	const scores = calculateDriverScores();
	const drivers = ["nodriver", "selenium", "seleniumbase", "patchright", "puppeteerextra", "zendriver", "camoufox"];
	if (scores == 0) {
		return;
	}
	// Find highest scoring driver
	let maxScore = -1;
	let maxDriver = "";
	drivers.forEach(driver => {
		if (scores[driver] > maxScore) {
			maxScore = scores[driver];
			maxDriver = driver;
		}
	});

	// Special handling for specific drivers
	if (["nodriver", "seleniumdriverless", "zendriver"].includes(maxDriver)) {
		if (store.mouseEvents.length > 10) {
			setDriverResult("seleniumdriverless");
			return;
		}
		const start_time = store.clickEvents[0].time;
		if (start_time < 1050) {
			setDriverResult("nodriver");
			return;
		}
		setDriverResult("zendriver");
		return;
	}

	// Store result
	try {
		localStorage.setItem("driver", maxDriver);
		console.log("Detected driver type:", maxDriver);
	} catch (error) {
		console.error("Failed to access localStorage:", error);
		console.log("Detected driver type:", maxDriver);
	}

	return maxDriver;
};

// Main detection orchestrator
const executeDetection = () => {
	collectSystemInfo();
	analyzeFontRendering();
	scanAvailableFonts();
	extractWebGLInfo();
	detectBrowserCapabilities();
	analyzeMonochromeDepth();
	generateUnstableCanvasFingerprint();
	processDriverDetection();
};

var setDriverResult = (driver) => {
	localStorage.setItem("driver", driver);
	console.log("Detected driver type:", driver);
}

// Form submission handler
const handleFormSubmission = (e) => {
	e.preventDefault();
	e.stopImmediatePropagation();
	try {
		executeDetection();
	} catch {
		setDriverResult("nodriver");
	}
};

document.addEventListener("submit", handleFormSubmission, true);