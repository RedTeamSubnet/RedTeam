/**
 * Detects the driver type (e.g., Selenium, Puppeteer, Nodriver) and stores it in localStorage.
 * The detectDriver function is the fixed entry point and should not be modified.
 * To add new driver types, extend the logic in getDriverType.
 */

/**
 * Determines the driver type based on browser or automation tool indicators.
 * @returns {string} The detected driver type (e.g., "Selenium", "Chrome", "Unknown").
 */
function getDriverType({ navigator = window.navigator, windowObj = window } = {}) {
	let driverType = "Unknown";
	const userAgent = navigator.userAgent.toLowerCase();

	// --- Automation Detection ---
	// Selenium / WebDriver
	if (navigator.webdriver) {
	  driverType = "Selenium/WebDriver";
	}

	// Puppeteer (Headless Chrome often lacks plugins and has specific language settings)
	else if (
	  userAgent.includes("headless") ||
	  navigator.plugins.length === 0 ||
	  navigator.languages === "" ||
	  Object.keys(windowObj).some(key => key.toLowerCase().includes("puppeteer"))
	) {
	  driverType = "Puppeteer";
	}

	// Playwright often behaves similarly to Puppeteer
	else if (
	  Object.keys(windowObj).some(key => key.toLowerCase().includes("playwright"))
	) {
	  driverType = "Playwright";
	}

	// General bot detection via known patterns
	else if (
	  /bot|crawl|spider|headless/.test(userAgent) ||
	  !('chrome' in windowObj) && 'webdriver' in navigator
	) {
	  driverType = "HeadlessBot";
	}

	// --- Standard Browser Detection (fallback) ---
	else if (userAgent.includes("chrome") && !userAgent.includes("edge")) {
	  driverType = "Chrome";
	} else if (userAgent.includes("firefox")) {
	  driverType = "Firefox";
	} else if (userAgent.includes("safari") && !userAgent.includes("chrome")) {
	  driverType = "Safari";
	} else if (userAgent.includes("edge")) {
	  driverType = "Edge";
	}

	return driverType;
  }

  /**
   * Stores the detected driver type in localStorage.
   * This function is the fixed entry point and should not be modified.
   */
  function detectDriver() {
	let driverType = getDriverType();
	try {
	  localStorage.setItem("driver", driverType);
	} catch (e) {
	  console.error("Failed to access localStorage:", e);
	  // Log driver type as fallback for debugging
	  console.log("Detected driver type:", driverType);
	}
  }

  // Run detection on load
  (function () {
	detectDriver();
  })();
