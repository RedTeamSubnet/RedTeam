# Miner Manual: Device Fingerprinting Challenge

## Table of Contents

1. [Challenge Overview](#challenge-overview)
2. [Environment Setup](#environment-setup)
3. [Device Configuration](#device-configuration)
4. [API Reference](#api-reference)

## Challenge Overview

The Device Fingerprinting challenge (dev_fingerprinter_v1) tests your ability to create a robust solution for fingerprinting iOS devices. The goal is to develop techniques that can uniquely identify and differentiate between iOS devices, even when they are similar models.

### Objectives

- Develop fingerprinting techniques for iOS devices
- Create unique device identifiers
- Handle device state management
- Implement reliable communication with iOS devices via shortcuts
- Build a scalable solution that works across multiple device pairs

## Environment Setup

### Infrastructure Components

- **6 iPhone devices** organized in 3 pairs of identical models
- **Pushcut Server** running on each device for remote automation
- **Specialized Proxy Server** at <https://github.com/RedTeamSubnet/rest.dfp-proxy>
- **Tailscale Network** for secure device communication
- **Configuration Management** via devices.json

## Device Configuration

### devices.json Structure

```json
[
  {
    "id": 1,
    "ts_node_id": "node_id",
    "ts_name": "my-iphone.tail123.ts.net",
    "ts_ip": "100.64.0.1",
    "pushcut_id": "my-iphone",
    "pushcut_api_key": "jPH2Lacs7ygioCEX",
    "pushcut_server_id": "12345678-1234-1234-1234-123456789012",
    "device_model": "my-iphone-model",
    "fingerprint": null,
    "state": "NOT_SET",
    "status": "INACTIVE"
  }
]
```

### Configuration Fields Explained

| Field | Description | Usage |
|-------|-------------|-------|
| `id` | Unique device identifier | Primary key for device reference |
| `ts_node_id` | Tailscale node ID | Network identification via Tailscale API |
| `ts_name` | Tailscale hostname | Network addressing |
| `ts_ip` | Tailscale IP address | Direct IP communication |
| `pushcut_id` | Device slug reference | Human-readable identifier |
| `pushcut_api_key` | Pushcut authentication | API access credential |
| `pushcut_server_id` | Pushcut server identifier | Target server selection |
| `device_model` | iPhone model information | Device categorization |
| `fingerprint` | Generated device fingerprint | Result storage |
| `state` | Current processing state | Workflow tracking |
| `status` | Device availability | Resource management |

## API Reference

### Pushcut API Endpoints

#### List Servers

```http
GET https://api.pushcut.io/v2/servers
```

**Headers:**

- `API-Key`: Your Pushcut API key

### Tailscale API Integration

#### List Devices

```http
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices
```

**Headers:**

- `Authorization`: Bearer {api_key}

## References

- [Pushcut API Documentation](https://www.pushcut.io/support/api)
- [Tailscale API Documentation](https://tailscale.com/api)
- [rest.dfp-proxy Repository](https://github.com/RedTeamSubnet/rest.dfp-proxy)