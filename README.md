## TideTrace

This repository contains a small static web app, TideTrace.
TideTrace is a local-first, privacy-conscious health journaling app focused on user control over pain and medical-context records.

TideTrace is designed around user control over pain and medical-context records.
Pain, medication, and health-related notes can be highly sensitive. 
For this reason, TideTrace keeps user-entered data in the browser and does not send it to an external server. 
The goal is not only privacy, but also to help users keep control over how their records are stored, reviewed, exported, summarized, and shared with healthcare professionals.

TideTrace does not provide medical advice, diagnosis, medication timing advice, or emergency guidance. It is a record-keeping tool intended to support users in organizing their own observations.

The app is published from the `docs/` folder using GitHub Pages.

## Privacy rules

- Do not commit real health records.
- Do not commit medication logs.
- Do not commit personal notes.
- Do not commit CSV or JSON backup files.
- User-entered data must stay in the browser.
- The app must not send data to external servers.
- The app must not use analytics, tracking, external APIs, or third-party libraries.

## GitHub Pages

Publishing source:

- Branch: `main`
- Folder: `/docs`

The published site contains only the app code.  
Actual log data is stored in the user’s browser and should be exported manually as CSV or JSON when needed.

## Safety note

This app is for recording only.  
It does not provide medical advice, medication timing advice, or emergency guidance.

## License

The source code is licensed under the MIT License. See [LICENSE](LICENSE) for details.
