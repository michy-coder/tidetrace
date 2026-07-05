# Tide Trace

Tide Trace is a small local-first logging app.
User-entered TideTrace records are stored in the browser's localStorage and are not sent to a TideTrace application server.
Cloudflare Web Analytics may be present on the published page for public page-usage analytics; it is separate from TideTrace record data. No external API, cloud sync, or login is used.

Open `index.html` through GitHub Pages or a local static file server. On first launch, import a settings JSON such as `sample-settings.json`.
