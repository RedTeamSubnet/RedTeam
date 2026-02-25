---
title: Testing Manual
---

# Device Fingerprinter (DFP) Testing Manual

The **Miner Testing Sandbox** is the primary tool for developing and validating your `fingerprinter.js` script. It allows you to test your logic in isolation without the overhead of a full challenge session.

## Why use the Sandbox?

1.  **Isolated Testing**: Validate your `fingerprinter.js` immediately across different browser profiles.
2.  **Performance Evaluation**: The sandbox uses the official "Two-Strike" rule to measure:
    -   **Fragmentation (Internal Consistency)**: Ensures the same device consistently produces the same hash across different browsers.
    -   **Collision (External Uniqueness)**: Ensures different devices produce unique hashes.
3.  **Real-time Results**: View a breakdown of "Correct," "Collisions," and "Fragmentations" to see exactly where your script needs improvement.

---

## Quick Start Guide

### Step 1: Setup the Proxy Environment
You only need the DFP Proxy repository for testing:
```bash
git clone git@github.com:RedTeamSubnet/rest.dfp-proxy.git dfp_proxy
cd dfp_proxy

# Create the environment file (required for the app to start)
cp .env.example .env
```

### Step 2: Provide Your Script
Paste your implementation logic into:
`src/api/static/js/fingerprinter.js`

### Step 3: Start the Sandbox
```bash
./compose.sh start -l
```

### Step 4: Run Your Tests
1.  **Open the Dashboard**: Visit **`http://localhost:8000/miner-test`** in your browser.
2.  **Label Your Device**: Enter a name (e.g., `my-laptop`) and click **Submit Fingerprint**.
3.  **Test Consistency (Fragmentation)**: 
    - Open the same URL in a **different browser engine** (e.g., switch from Chrome to Brave or Safari).
    - Use the **exact same Device Label**.
    - Click Submit again. If your hash changed, you will see a **Fragmentation** error.
4.  **Test Uniqueness (Collision)**: 
    - Ask a friend to visit the URL or use a different physical machine.
    - Use a **different Device Label** (e.g., `office-pc`).
    - Click Submit. If they produce the same hash as you, you will see a **Collision** error.

---

## Development Workflow

-   **View Results**: Click the **View Results** button at any time to see your current score and a detailed list of all collected hashes.
-   **Clean Session**: Use the **Clean Session** button to wipe all test data and restart your testing cycle immediately.
-   **Final Goal**: Aim for a **1.0 Score** in the sandbox with multiple browsers and devices before submitting your final commit.
