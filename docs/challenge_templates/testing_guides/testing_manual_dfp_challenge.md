# Digital Fingerprinting (DFP) Challenge Testing Manual

This manual provides instructions for testing the Digital Fingerprinting (DFP) challenge using the PDX repository.

## Overview

- Tests miner's ability to create unique digital fingerprints
- Includes multi-device testing on the same network
- Uses custom fingerprinting scripts for detection avoidance

## Quick Start Guide

### Prerequisites

- Git (for cloning the repository)
- Multiple devices on the same network (for testing)
- Web browser access

### Step 1: Clone the Repository

```bash
git clone https://github.com/RedTeamSubnet/rest.dfp-proxy.git
cd rest.dfp-proxy.git
```

### Step 2: Provide Your Fingerprinting Script

- Place your custom fingerprinting script into `src/api/static/js/fingerprinter.js`
- Ensure your script implements the required fingerprinting methods
- Ensure you can see fingerprint by console log. Here is the example:

    ```js
    console.log("[Fingerprinter] Starting...");
    console.log("[Fingerprinter] Generated fingerprint:", hash);
    console.log("[Fingerprinter] Completed.");
    ```

### Step 3: Setup Testing Environment

```bash
./scripts/setup-test-env.sh
```

### Step 4: Test Your Script

- Open the testing page on multiple devices within the same network
- Verify that each device generates a unique fingerprint
- Test the script's ability to avoid detection mechanisms

## Testing Steps

1. **Single Device Test**: Test your script on one device first to ensure basic functionality
2. **Multi-Device Test**: Open the same page on different devices (phones, tablets, laptops) connected to the same network
3. **Fingerprint Uniqueness**: Verify that each device produces a distinct fingerprint even with different browser

## Important Notes

- Make sure all devices are connected to the same network for accurate testing
- The fingerprinting script should generate unique identifiers for each device
- Test across different browsers and device types for comprehensive coverage
- Monitor for any detection alerts or blocking mechanisms

## Troubleshooting

If you encounter issues:

1. Verify that the setup script completed successfully
2. Check network connectivity between devices
3. Test with different browsers if issues persist
4. Check console logs for any JavaScript errors
