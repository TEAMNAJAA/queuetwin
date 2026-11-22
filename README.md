# QueueTwin AI — 3D Hospital Queue Digital Twin

Built during EvoHacks 2.0 · Theme: Projects for Social Good

## Live demo
`https://<your-vercel-link>` — opens with a simulated 09:00 morning rush. Click **🧪 Simulate Test Crowd** to turn the bots off.

## Sponsor integrations (real)
| Sponsor | What it does in QueueTwin | How |
|---|---|---|
| **Agentboxd** | Sends queue / best-time emails, creates pharmacy restock **drafts** that a human approves before sending, reads inbound patient replies | `POST /v1/inboxes/{id}/messages/send`, `POST /v1/inboxes/{id}/drafts`, `GET /v1/inboxes/{id}/messages` via the server proxy `api/agentboxd.js` |
| **MojoAuth** | Passwordless email OTP so patients and family can verify on the tracking page without a password | `POST /users/emailotp` + `/users/emailotp/verify` via `api/mojoauth.js` |
| SSOJet | **Not connected** in this build. The staff-role button is a demo role switch. Planned: OIDC + PKCE | — |

API keys live only in Vercel environment variables. The browser never sees them.
If a key or the proxy is missing, the app shows a labelled **Sandbox** message and sends nothing.

## Run / deploy
1. Import this repo into Vercel (no build step).
2. Add environment variables: `AGENTBOXD_API_KEY`, `AGENTBOXD_INBOX_ID` (inbox UUID), `MOJOAUTH_API_KEY`.
3. Deploy. Opening `index.html` directly from disk also works, but sponsor actions will run in Sandbox mode.

Cross-device queue tracking: paste a Firebase Realtime Database URL in **☁️ Mobile Cloud Sync**.

## Honest limits
- Patients, timings and the 09:00 crowd are simulated. Not connected to a real hospital system.
- Privacy masking hides surnames and clinical details on public QR/cloud data. This is a privacy-by-design prototype, not a certified (HIPAA/PDPA) system.

## Built during the event / pre-existing
Everything here was written during EvoHacks 2.0. External libraries: Three.js, qrcode-generator (CDN).
AI assistance: AI tools helped write parts of the code. The idea, design decisions and testing are ours, and we can explain every part.
