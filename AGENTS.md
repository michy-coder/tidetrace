# AGENTS.md

## Rules

- Do not commit secrets, API keys, passwords, tokens, or personal information.
- Do not modify the main branch directly.
- Create changes as a pull request.
- Do not add new external dependencies unless necessary.
- Ask before enabling network access or adding third-party services.

## Guidelines

- Prefer small, simple changes.
- Reuse existing code, UI patterns, and data structures before adding new ones.
- Keep the app local-first. Do not add server-side storage, external sync, analytics, or tracking unless explicitly requested.
- Keep medical-context text limited to record-keeping support. Do not add medical advice, diagnosis, medication timing advice, or emergency guidance.

## Checks before finishing

- Explain every changed file.
- If tests are available, run them before finishing.
- If no tests are available, explain what was checked manually.
  
## GitHub Pages app rules

- Put the static web app in `docs/`.
- Do not put user data in the repository.
- Do not add sample health records, real medication names, real notes, family information, school information, or company information.
- Do not add analytics, tracking, external APIs, external libraries, or server-side code.
- Do not send data outside the browser.
- Do not provide medical advice or medication timing recommendations.
- The app is for logging only.
- Keep the app usable on an iPhone in portrait orientation.
- Use plain HTML, CSS, and JavaScript.

## Data safety

- Preserve compatibility with existing localStorage data.
- Do not rename storage keys, event fields, or settings fields unless a migration is included.
- Do not silently drop existing user data during backup, restore, import, export, edit, or delete operations.
- If a data structure change is necessary, explain the migration path and any compatibility risk.

## Medical-context boundaries

- Keep TideTrace as a record-keeping and review-support tool.
- Do not add diagnosis, treatment recommendations, medication timing advice, emergency triage, or severity judgment.
- Use neutral wording for health-related summaries. The app may organize user-entered observations, but must not interpret them as medical conclusions.

## Manual checks

When relevant, manually check the affected flow before finishing:

- Add pain, medication, and note records.
- Edit and delete existing records.
- Export and restore a JSON backup.
- Export CSV files.
- Check today’s records and past records display.
- Check mobile Safari layout assumptions when UI is changed.

## Changelog

- Do not update CHANGELOG.md for minor UI text edits, small CSS adjustments, code cleanup, or internal refactoring.
- Update CHANGELOG.md only for changes that affect how users record, review, edit, export, import, summarize, or compare their data.
- Add new user-facing features under Unreleased > Added.
- Add behavior changes under Unreleased > Changed.
- Add user-visible bug fixes under Unreleased > Fixed.
- Do not modify past release sections.
- Do not rewrite, reorder, or reorganize CHANGELOG.md.
- If the change is borderline, do not edit CHANGELOG.md. Instead, mention in the final summary that a changelog entry may be appropriate.

## Specification documentation

When changing TideTrace behavior, check whether `/specs/SPEC.md` or `/specs/DATA_FORMAT.md` also needs to be updated.

Update `SPEC.md` for user-visible behavior, user flows, settings, import/export, editing/deletion, period comparison, and UI wording principles.

Update `DATA_FORMAT.md` for localStorage keys, schemaVersion, settings, event fields, period fields, JSON backup format, CSV export format, and compatibility or migration behavior.

Document only the current implementation. Do not invent planned behavior. If unclear from the code, write “Unknown from current implementation”.
