# GitHub Integration

How firmware repos use HIL benches for automated testing.

## Architecture

```
Firmware Repo                        HIL Bench (Pi)
┌──────────────┐                     ┌──────────────┐
│ push/PR      │                     │ GitHub Runner │
│   ↓          │                     │   ↓          │
│ Build job    │                     │ HIL test job │
│ (ubuntu-latest)   ──artifacts──▶   │ (self-hosted) │
│   ↓          │                     │   ↓          │
│ Upload .bin  │                     │ benchctl     │
└──────────────┘                     │ flash/serial │
                                     └──────────────┘
```

## Runner Registration

The bootstrap script registers the Pi as an **org-level** runner for `Aharoni-Lab`. This means any repo in the org can target the bench — no per-repo runner setup needed.

Runner labels (configured in `/etc/hil-bench/config.yaml`):

```yaml
runner:
  labels: [self-hosted, linux, ARM64, hil, samd51, bench01]
```

## Workflow Setup

### 1. Copy the example workflow

Copy `examples/firmware-ci.yml` to your firmware repo:

```bash
cp examples/firmware-ci.yml .github/workflows/hil-test.yml
```

### 2. Customize the workflow

Key parts to customize:

- **Build step**: Replace `make build` with your actual build command
- **Firmware path**: Match the artifact upload/download paths
- **Target name**: Use the target name from your bench config
- **Runner labels**: Match the labels on your bench
- **Concurrency group**: Prevents multiple jobs on the same bench

### 3. Concurrency

Only one HIL test should run per bench at a time. Use a concurrency group:

```yaml
concurrency:
  group: hil-samd51-bench01
  cancel-in-progress: false  # don't kill running tests
```

Setting `cancel-in-progress: false` ensures a flash operation isn't interrupted mid-way.

## Artifact Passing

The build job uploads the firmware binary, and the HIL test job downloads it:

```yaml
# Build job
- uses: actions/upload-artifact@v4
  with:
    name: firmware
    path: build/firmware.bin

# HIL test job
- uses: actions/download-artifact@v4
  with:
    name: firmware
- run: benchctl flash --firmware firmware.bin --target samd51
```

## Typical Test Flow

1. **Flash**: `benchctl flash --firmware firmware.bin --target samd51 --verify`
2. **Wait for boot**: `benchctl serial expect --pattern "BOOT OK" --timeout 15`
3. **Run tests**: Send commands via serial, check responses
4. **Check GPIO**: Verify no fault conditions
5. **Report**: Exit code propagates to GitHub (0 = pass, nonzero = fail)

## Multiple Benches

For multiple benches, give each unique labels:

```yaml
# Bench 1 config
runner:
  labels: [self-hosted, linux, ARM64, hil, samd51, bench01]

# Bench 2 config
runner:
  labels: [self-hosted, linux, ARM64, hil, samd51, bench02]
```

Workflows target specific benches:

```yaml
runs-on: [self-hosted, hil, samd51, bench01]
```

Or any available bench:

```yaml
runs-on: [self-hosted, hil, samd51]
```
