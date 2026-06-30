# TideTrace plugin marketplace

This directory contains the Codex plugin marketplace configuration for this repository.

## Ponytail plugin

The `ponytail` entry makes the Ponytail Codex plugin available from:

https://github.com/DietrichGebert/ponytail.git

Ponytail is listed as an optional Productivity plugin. It is not installed by default, and Codex prompts for authentication during installation when authentication is required by the source repository or environment.

This marketplace entry does not change the TideTrace GitHub Pages app, does not add runtime code to `docs/`, and does not send TideTrace browser records outside the user's browser.

## Maintenance notes

- Keep the marketplace file at `.agents/plugins/marketplace.json`.
- Keep plugin entries small and explicit.
- Do not add analytics, external APIs, or app runtime dependencies through plugin marketplace changes.
- Do not commit credentials or personal data in marketplace configuration.
