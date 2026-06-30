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
