# TideTrace

TideTrace is a small static web app for local-first pain, medication, and note logging.

It is designed to help users keep sensitive medical-context records in their own browser, review those records over time, create descriptive summaries, and take selected information with them when needed.

The app UI is currently Japanese. English documentation is provided for the project overview, privacy model, and development context.

Live app:

https://michy-coder.github.io/tidetrace/

Japanese documentation:

* Introduction: https://note.com/tidetrace/n/n2908ecde3b0e
* User guide: https://note.com/tidetrace/n/n6d64e28fea65

These documentation pages are written in Japanese. Depending on the reader’s browser or Note settings, they may be machine-translated.

## Purpose

Pain, medication, and health-related notes can be highly sensitive. They can also be difficult to reconstruct accurately from memory.

TideTrace helps users record observations when they occur and review them later. The goal is to reduce reliance on memory alone and make it easier to organize information before a medical appointment or other personal review.

TideTrace does not diagnose, interpret, or treat pain. It does not provide medical advice, treatment recommendations, medication timing advice, emergency guidance, or severity judgments.

## Why structured records matter

Pain communication can be affected by memory, time pressure, communication style, and bias.

TideTrace allows users to keep time-based records that combine:

* pain scores
* pain states or contexts
* medication records
* short notes
* dates and times

The purpose of these records is not to make pain objective or determine the effect of treatment. The purpose is to give users more ways to review and describe their own observations.

## Features

### Recording and review

TideTrace currently supports:

* pain records with a score and configurable pain state
* medication records using configurable medication buttons
* standalone notes
* optional notes attached to pain or medication records
* today’s records
* past records grouped by date
* editing record dates, times, and contents
* deleting individual records
* copying summaries of the currently displayed past records
* configurable periods for later comparison and review

Medication buttons and pain-state labels can be added, edited, reordered, hidden, and shown again. Hiding an option does not remove existing records.

### Record summaries

Users can select a date range and generate a descriptive record summary containing:

* medication totals and daily averages
* pain summaries by pain state
* pain summaries by time of day
* pain summaries grouped by recorded medication dose
* recorded pain-score changes before and after medication when matching records are available

These summaries organize recorded values only. They do not assess medication effectiveness, identify causes, or provide medical conclusions.

Generated summaries can be:

* copied as text
* saved as a plain text file
* printed or saved as a PDF through the browser’s print interface

### Past records and healthcare data

TideTrace can temporarily load a HeartWatch summary CSV file and display selected HeartWatch reference values beside TideTrace records by date.

This view supports:

* daily TideTrace pain summaries
* medication record counts
* standalone note counts
* selected HeartWatch summary values, including heart-rate, activity, sleep, and other available fields
* configurable display columns
* configurable column order
* short custom column labels
* readable text copying
* TSV copying
* printing or PDF saving through the browser’s print interface

The importer accepts HeartWatch summary CSV files only. It is not a direct Apple Health or HeartWatch account integration.

Imported HeartWatch data is kept temporarily in memory for the current page. It is not saved to `localStorage`, included in TideTrace JSON backups, or uploaded to a TideTrace application server. Reloading or closing the page clears the imported data.

### Backup and export

TideTrace supports:

* exporting a complete JSON backup
* restoring records and settings from a TideTrace JSON backup
* exporting all records as CSV
* exporting only pain records, medication records, or standalone notes as CSV

JSON backup is intended for restoring TideTrace data. CSV, text, TSV, printing, and PDF saving are intended for reviewing or taking selected information outside the app.

Users should save JSON backups regularly if they need to preserve their records.

## Storage and privacy

TideTrace is published as a static web app from the `docs/` folder using GitHub Pages.

Pain records, medication records, notes, settings, periods, and export timestamps are stored in browser `localStorage`.

TideTrace does not send user-entered records to a TideTrace application server. User records are not stored in this repository or on GitHub Pages.

Because browser storage can be cleared or lost depending on browser or device conditions, users are responsible for saving backups when needed. Private browsing may not retain records reliably.

TideTrace does not use:

* server-side storage for user-entered records
* external sync for user-entered records
* external APIs for app features or record processing
* third-party libraries for app functionality
* advertising trackers
* analytics for user-entered health records or in-app health-related actions

## Analytics

TideTrace uses Cloudflare Web Analytics to understand basic public page usage, such as page views, visit counts, referrers, approximate region, browser, and device type.

Cloudflare Web Analytics is separate from TideTrace record storage and processing.

It is not used to analyze:

* pain records
* medication records
* notes
* imported HeartWatch data
* in-app health-related actions
* data stored in browser `localStorage`

Analytics are used only to understand whether the public app page is being visited and how people generally reach it.

## Project rules

Health-related records must not be committed to this repository.

Do not commit:

* real health records
* medication logs
* personal notes
* imported healthcare CSV files
* TideTrace CSV export files
* TideTrace JSON backup files

The app must preserve compatibility with existing stored data and backups.

Changes must not add external record storage, automatic record synchronization, medical interpretation, or new tracking without an explicit project decision.

## GitHub Pages

Publishing source:

* Branch: `main`
* Folder: `/docs`

The published site contains the static application code. User-entered records remain in each user’s browser.

## Medical safety

TideTrace is a record-keeping and review-support tool.

It does not provide:

* medical advice
* diagnosis
* treatment recommendations
* medication timing advice
* emergency triage
* severity judgments

TideTrace summaries describe recorded observations. They do not determine whether treatment is effective, explain why symptoms occurred, or decide whether medical care is needed.

Questions about treatment, medication use, symptoms, or medical care should be discussed with an appropriate healthcare professional.

## License

The source code is licensed under the MIT License.

See `LICENSE` for details.
