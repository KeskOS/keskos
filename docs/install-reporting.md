# Install Reporting

KeskOS install reporting is explicit, opt-in, and proxy-based.

The client never sends directly to Discord.

Client destination:

```text
https://api.keskos.org/install-report
```

The Discord webhook must exist only on the server side as an environment variable such as:

```text
DISCORD_INSTALL_REPORT_WEBHOOK
```

Do not commit a Discord webhook URL into:

- the ISO
- `Kesk Welcome`
- Calamares scripts
- shell helpers
- docs intended for the client side
- Git history

## Installer Flow

The ISO installer now sends the basic install report during the Calamares flow itself.

Current behavior:

- successful installs are sent from the installer post-install hook
- failed installs are sent from the Calamares wrapper after a non-zero exit
- report sending never blocks the installer
- HTTP `202` is treated as success

## Welcome Follow-Up

`Kesk Welcome` still exposes install reporting on the final page under `INSTALL REPORT`.

Current follow-up behavior:

- if the installer already sent the basic report, `Kesk Welcome` skips a duplicate send only when it has no new report fields to add
- if `Kesk Welcome` adds browser, widget, optional-app, or other new report fields, it sends a sanitized follow-up payload
- if the user enables extra diagnostics, `Kesk Welcome` may send a follow-up payload with those extra diagnostics

## What The Basic Report Sends

Allowed default fields:

- `install_result`
- `install_duration_seconds`
- `keskos_version`
- `iso_build_id`
- `installer_version`
- `kernel_version`
- `calamares_version`
- `install_mode`
- `boot_mode`
- `filesystem_selected`
- `desktop_profile_selected`
- `browser_selected`
- `top_bar_widgets_selected`
- `optional_apps_selected`
- `failed_stage`
- `sanitized_error_summary`
- `timestamp_utc`
- `timezone`
- `locale_language`
- `cpu_model`
- `ram_amount`
- `disk_size`
- `gpu_vendor_model`
- `network_online_during_install`
- `package_install_success_count`
- `package_install_fail_count`

## What Is Never Sent

The client must not send:

- username
- hostname
- IP address
- MAC address
- Wi-Fi SSID
- passwords
- tokens
- personal files
- exact location
- disk serial numbers

## Sanitization

Before sending, the client sanitizes strings to remove or replace:

- `/home/<user>` paths
- detected usernames
- detected hostnames
- IPv4 addresses
- MAC addresses
- password/token style key-value strings

Long error-style strings are truncated.

## Extra Diagnostic Details

Extra diagnostics are only included when the user explicitly enables them on the final page.

Current extra diagnostics are limited to non-personal setup state such as:

- welcome mode: first-run / rerun / manual
- browser action result summaries
- top bar action result summary
- optional apps action result summary
- theme action result summary
- network backend availability and uplink result

These values are sanitized before send as well.

## Current Scope

The current implementation sends:

- a basic installer report automatically from the ISO installer for successful installs
- a basic installer report automatically when the installer exits with a failure status
- an optional follow-up report from `Kesk Welcome` only when extra diagnostics are explicitly enabled

The current failure path uses a sanitized summary extracted from the Calamares debug log and a heuristic stage name when available.

## Temporary Files And Local Logs

Temporary payload file:

```text
/tmp/keskos-install-report.json
```

The payload file is removed after send success or failure.

Local user log:

```text
~/.local/state/kesk/logs/install-report.log
```

The local log records:

- installer success send requested
- installer failure send requested
- the payload keys, version, and iso build id that were posted
- whether extra diagnostics were enabled for follow-up sends
- whether the send was skipped offline
- whether the server request succeeded or failed

The local log does not record secrets.

## Installer-Side Source Data

The installer records a local source summary for the later opt-in report path.

Current files:

- `/tmp/keskos-install-session.json`
- `/var/lib/keskos/install-session.json`
- `/var/lib/keskos/install-report-source.json`
- `/etc/keskos/install-report-sent.json`

These are used to carry non-personal install facts such as timing, build ID, selected install profile, and package success counts into the first logged-in session.

## Failure Behavior

Install reporting must never block setup completion.

Rules:

- if offline, skip reporting
- if the proxy endpoint fails, log it locally
- if the helper fails, do not fail the install or `Kesk Welcome`
- do not retry forever
- keep the JSON payload under 64kb

## Disabling Reporting

For end users:

- leave `Send basic install report` unchecked on the final page

For distro builders or local forks:

- remove or replace the final-page report UI in the standalone `KeskOS/keskos-welcome` source tree
- remove or replace `airootfs/usr/lib/kesk/install_report.py`
- remove the installer-side source capture if reporting is not wanted

## Server Proxy Responsibilities

The proxy endpoint must:

- rate limit requests
- validate the JSON schema
- reject oversized payloads
- drop disallowed fields if present
- keep the Discord webhook only in `DISCORD_INSTALL_REPORT_WEBHOOK`
- forward only a sanitized summary to Discord

Example server code:

- [docs/examples/install-report-proxy.py](/home/geko/Documents/scripts/keskos/docs/examples/install-report-proxy.py)

## Webhook Rotation

If the Discord webhook is ever leaked:

1. Revoke or delete the webhook in Discord.
2. Create a new webhook.
3. Update the server environment variable:
   `DISCORD_INSTALL_REPORT_WEBHOOK`
4. Restart the proxy service.
5. Do not change the client endpoint unless the proxy URL itself changed.
