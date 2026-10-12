# Portainer (Filtered) - Home Assistant Custom Integration

A high-performance fork of Home Assistant's official **Portainer** core integration that adds granular **Endpoint / Server selection** and **Entity Type filtering** directly in the Home Assistant UI.

[![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

---

## 🎯 Why This Fork Exists

The official Home Assistant Portainer integration imports **everything** Portainer has access to across all connected Docker environments. In multi-server homelabs, this often causes:
1. **Massive Entity Registry Bloat**: Docker generates hundreds of anonymous hash volumes over time, causing the official integration to create **700+ anonymous volume sensors** (`volume_driver`, `volume_size`).
2. **Duplicate Monitoring**: If you already run the native Unraid integration or host-specific monitoring, Portainer duplicates every Unraid container.
3. **Broken Auto-Update Automations**: The official integration exposes container image digests as `update.*` entities. Generic HA auto-update automations attempt to install them at night, causing 1-hour timeouts and failure alerts.

This fork solves all three problems with zero compromise on functionality.

---

## ✨ Features

- **Multi-Server / Endpoint Picker**: Choose exactly which Portainer endpoints (e.g. `Omada Pi`, `Ubuntu Developer VM`) to monitor in Home Assistant, while excluding hosts you already monitor natively (like `Unraid`).
- **Volume Entity Toggle**: Disable Docker volume sensors (default: **OFF**), immediately preventing hundreds of ghost volume devices from cluttering your entity registry.
- **Container Update Entity Toggle**: Disable `update.*` entities (default: **OFF**), permanently preventing nightly auto-update scripts from stalling on container images.
- **Granular Platform Toggles**: Individually enable or disable container control buttons (Restart, Recreate, etc.), power switches, and resource metrics (CPU/RAM).
- **Automatic Registry Cleanup**: When you exclude an endpoint or disable volumes, existing entities and devices are automatically pruned from Home Assistant on reload.
- **Upstream Currency**: Synchronized with Home Assistant Core releases via GitHub Actions.

---

## ⚙️ Configuration

Once installed, go to **Settings > Devices & Services > Portainer > Configure**:

```
┌────────────────────────────────────────────────────────┐
│                   Portainer Options                    │
├────────────────────────────────────────────────────────┤
│ Endpoints / Servers to monitor:                        │
│   [ ] Unraid (ID: 1)                                   │
│   [✓] Omada Pi (ID: 2)                                 │
│   [✓] Ubuntu Developer VM (ID: 3)                      │
│                                                        │
│ Entity Types & Platforms:                              │
│   [ ] Enable Docker volume entities                    │
│   [ ] Enable container image update entities           │
│   [✓] Enable container resource sensors (CPU, RAM)     │
│   [✓] Enable container control buttons                 │
│   [✓] Enable container power switches                  │
│                                                        │
│                    [ Submit ]                          │
└────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Method 1: Via HACS (Recommended)
1. In Home Assistant, open **HACS**.
2. Click the three dots in the top right corner ➔ **Custom repositories**.
3. Add the repository URL: `https://github.com/Rutj87/ha-portainer-custom` (Category: **Integration**).
4. Click **Download**, then restart Home Assistant.

### Method 2: Manual Installation
1. Copy the `custom_components/portainer` folder into your Home Assistant `/config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & Services > Portainer > Configure** to adjust your endpoints and filters.

---

## 🔄 Upstream Currency & Maintenance

This repository includes a GitHub Action (`.github/workflows/sync_upstream.yml`) that periodically checks `home-assistant/core:dev` for updates to `homeassistant/components/portainer`. When upstream updates are detected, an automated PR is created to merge official bugfixes while preserving our custom options flow.
