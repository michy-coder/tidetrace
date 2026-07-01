## TideTrace

TideTrace is a small static web app for local-first health journaling.
It is designed to help users record pain, medication, and health-related notes while keeping control over sensitive medical-context records.

The app UI is currently Japanese. English documentation is provided for project overview, privacy model, and development context. UI internationalization may be considered later if there is user or contributor demand.

Live app:

https://michy-coder.github.io/tidetrace/

Japanese documentation:

* Introduction: https://note.com/tidetrace/n/n2908ecde3b0e
* User guide: https://note.com/tidetrace/n/n6d64e28fea65

These documentation pages are written in Japanese.
Depending on the reader’s browser or Note settings, they may be machine-translated.

## Purpose

Pain, medication, and health-related notes can be highly sensitive.
For this reason, TideTrace keeps user-entered data in the browser and does not send it to an external server.

The goal is not only privacy.
TideTrace is also designed to help users keep control over how their records are stored, reviewed, exported, summarized, and shared with healthcare professionals.

TideTrace does not provide medical advice, diagnosis, medication timing advice, or emergency guidance.
It is a record-keeping tool intended to support users in organizing their own observations.

## Why structured records matter

Pain communication can be affected by memory, time pressure, communication style, and bias.
TideTrace does not attempt to diagnose, interpret, or treat pain.

Instead, it helps users keep a structured record of pain, medication, and context over time.
The goal is to make it easier for users to review their own observations and, when appropriate, share clearer summaries with healthcare professionals.

## Features

TideTrace currently supports:

* pain records
* medication records
* standalone notes
* configurable medication buttons
* configurable pain state labels
* today’s records
* past records
* consultation summaries
* CSV export
* JSON backup and restore

TideTrace is published as a static web app from the docs/ folder using GitHub Pages.

User-entered records are stored in the user’s browser. TideTrace does not send pain entries, medication entries, notes, backups, or other user-entered health records to an external server.

TideTrace may use Cloudflare Web Analytics to understand basic public page usage, such as page views, visit counts, referrers, approximate region, browser, and device type. Analytics are not used to track pain entries, medication entries, notes, button actions, or data stored in the browser.

TideTrace does not use:

* server-side storage for user-entered records
* external APIs for app features or record processing
* third-party libraries for app functionality
* advertising trackers
* analytics for user-entered health records or in-app health-related actions

Actual log data is stored in the user’s browser and should be exported manually as CSV or JSON when needed.
## Project rules

Health-related records must not be committed to this repository.

Do not commit:

* real health records
* medication logs
* personal notes
* CSV export files
* JSON backup files

User-entered data must stay in the browser.
The app must not send data to external servers.

## GitHub Pages

Publishing source:

* Branch: main
* Folder: /docs

The published site contains only the app code.
User records are not stored in this repository or on GitHub Pages.

## Analytics

TideTrace uses Cloudflare Web Analytics to understand basic public page usage, such as page views, visit counts, referrers, approximate region, browser, and device type.

TideTrace does not use analytics to track pain entries, medication entries, notes, button actions, or any data stored in the browser. User-entered health records remain in local browser storage and are not sent to Cloudflare by TideTrace.

Analytics are used only to understand whether the public app page is being visited and how people generally reach it.

## Medical safety

This app is for recording only.

It does not provide:

* medical advice
* diagnosis
* treatment recommendations
* medication timing advice
* emergency guidance

Users are responsible for deciding how to use their own records.
When in doubt or when concerned, they should consult a healthcare professional.

## License

The source code is licensed under the MIT License.
See LICENSE for details.
