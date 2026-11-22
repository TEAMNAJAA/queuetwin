const { limited, body, clean, EMAIL } = require('./_util');
const BASE = 'https://api.mojoauth.com';

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const key = process.env.MOJOAUTH_API_KEY;
  if (!key) return res.status(503).json({ ok: false, error: 'not_configured' });
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'method' });
  if (limited(req, 10)) return res.status(429).json({ ok: false, error: 'rate_limited' });
  const b = body(req);
  const H = { 'x-api-key': key, 'Content-Type': 'application/json' };
  try {
    if (b.action === 'send') {
      const email = clean(b.email, 254).trim();
      if (!EMAIL.test(email)) return res.status(400).json({ ok: false, error: 'bad_email' });
      const r = await fetch(`${BASE}/users/emailotp`, { method: 'POST', headers: H, body: JSON.stringify({ email }) });
      const d = await r.json().catch(() => ({}));
      return res.status(r.ok ? 200 : r.status).json({ ok: r.ok && !!d.state_id, status: r.status, state_id: d.state_id, error: r.ok ? undefined : (d.message || d.error || 'send_failed') });
    }
    if (b.action === 'verify') {
      const state_id = clean(b.state_id, 200).trim();
      const otp = clean(b.otp, 10).trim();
      if (!state_id || !/^\d{4,8}$/.test(otp)) return res.status(400).json({ ok: false, error: 'bad_input' });
      const r = await fetch(`${BASE}/users/emailotp/verify`, { method: 'POST', headers: H, body: JSON.stringify({ state_id, otp }) });
      const d = await r.json().catch(() => ({}));
      const ok = r.ok && d.authenticated !== false;
      return res.status(ok ? 200 : (r.ok ? 401 : r.status)).json({ ok, status: r.status, email: ok && d.user ? d.user.identifier || d.user.email : undefined });
    }
    return res.status(400).json({ ok: false, error: 'bad_action' });
  } catch (e) {
    return res.status(502).json({ ok: false, error: 'upstream_unreachable' });
  }
};
