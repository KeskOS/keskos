# Kesk Welcome

`Kesk Welcome` is the current KeskOS first-boot setup app.

This directory is a real adaptation of the CachyOS Welcome codebase. The Rust/GTK base was kept for stability, then reworked for KeskOS:

- full `KeskOS` / `Kesk Welcome` branding
- first-boot marker at `~/.config/kesk/welcome-complete`
- logs at `~/.local/state/kesk/logs/welcome.log`
- KeskOS browser/theme/tool integration
- numbered guided setup flow instead of the upstream CachyOS maintenance layout

## License / Attribution

This fork remains under the original GPL terms from CachyOS Welcome.

- Original upstream project: `CachyOS Welcome`
- Original upstream repository: `https://github.com/CachyOS/CachyOS-Welcome`
- KeskOS changes in this tree adapt the upstream Rust/GTK base for KeskOS first-boot use

See [LICENSE](LICENSE) for the full license text.
