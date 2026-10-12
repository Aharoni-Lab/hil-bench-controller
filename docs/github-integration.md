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

## ESP-IDF Firmware (ESP32-C6)

The receiver firmware repo uses a three-job workflow (`photodiode-lvds-receiver`,
`.github/workflows/esp32-firmware.yml`). Pattern:

1. `build` on `ubuntu-latest`: `espressif/esp-idf-ci-action@v1` with `esp_idf_version`,
   `target: esp32c6` and `path` set to the project; then a merged image
   (bootloader + partition table + app at offset 0x0) and an uploaded artifact.
   Action inputs: <https://github.com/espressif/esp-idf-ci-action>.
2. `host-tests` on `ubuntu-latest`: plain cmake + ctest, only if the project has a host test tree.
3. `hil-test` on `[self-hosted, hil, esp32c6]`, gated by a repository variable so it does
   nothing until a bench exists:

```yaml
hil-test:
  needs: build
  runs-on: [self-hosted, hil, esp32c6]
  # Bench exists (repo variable) AND not a fork PR (see "Self-hosted runner safety")
  if: ${{ vars.HIL_ESP32C6_BENCH == 'true' && (github.event_name == 'push' || github.event.pull_request.head.repo.full_name == github.repository) }}
  concurrency: { group: hil-esp32c6-receiver, cancel-in-progress: false }
  timeout-minutes: 15
  steps:
    - uses: actions/download-artifact@v4
      with: { name: esp32-firmware }
    - run: benchctl health --check config --check probe
    - run: benchctl flash --firmware receiver-esp32c6-merged.bin --target esp32c6_receiver
    - run: benchctl serial expect --target esp32c6_receiver --pattern "BOOT OK" --timeout 20
    - run: benchctl gpio get --pin hv_dis --target esp32c6_receiver --expect high
    - run: benchctl serial send --target esp32c6_receiver "selftest quick"
    - run: benchctl serial expect --target esp32c6_receiver --pattern '"pass":true' --timeout 60
```

`benchctl flash` returns only after the USB console port has re-enumerated, and
`benchctl serial` retries the open for a few seconds, so no sleeps are needed between
steps. See [esp32-targets.md](esp32-targets.md). Untested on hardware.

## Self-hosted runner safety

A workflow that runs on the bench executes whatever the pull request contains, on a machine
wired to real hardware. Do not let untrusted code reach it:

- Gate the HIL job so fork pull requests never run on the bench:
  `if: ${{ github.event_name == 'push' || github.event.pull_request.head.repo.full_name == github.repository }}`
  (combine with other conditions using `&&`, as in the ESP-IDF snippet above).
- In the repository (or org) settings under Actions > General, set fork pull request
  workflows to "Require approval for all outside collaborators".
- Put the runner in a runner group limited to the intended repositories (org Settings >
  Actions > Runner groups), not the default group open to every repository.
- Consider registering the runner with `--ephemeral` (one job, then it deregisters). The
  bootstrap does not do this: `install_runner.sh` registers one persistent runner under a
  systemd service, and an ephemeral runner would need re-registration (a fresh token) after
  every job, so it is a recommendation only.

Reference: <https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners#self-hosted-runner-security>

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
