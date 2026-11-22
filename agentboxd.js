const { limited, body, clean, EMAIL } = require('./_util');
const BASE = 'https://api.agentboxd.com/v1';

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const key = process.env.AGENTBOXD_API_KEY;
  const inbox = process.env.AGENTBOXD_INBOX_ID;
  if (!key || !inbox) return res.status(503).json({ ok: false, error: 'not_configured' });
  if (limited(req)) return res.status(429).json({ ok: false, error: 'rate_limited' });
  const H = { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };
  const ib = encodeURIComponent(inbox);
  const action = (req.query && req.query.action) || body(req).action;
  try {
    let r;
    if (req.method === 'GET' && action === 'status') {
      r = await fetch(`${BASE}/inboxes/${ib}`, { headers: H });
    } else if (req.method === 'GET' && action === 'poll') {
      r = await fetch(`${BASE}/inboxes/${ib}/messages?direction=inbound&limit=5`, { headers: H });
    } else if (req.method === 'POST' && (action === 'send' || action === 'draft')) {
      const b = body(req);
      const to = clean(b.to, 254).trim();
      const subject = clean(b.subject, 200).trim();
      const text = clean(b.text, 4000);
      if (!EMAIL.test(to)) return res.status(400).json({ ok: false, error: 'bad_recipient' });
      if (!subject) return res.status(400).json({ ok: false, error: 'missing_subject' });
      const path = action === 'send' ? 'messages/send' : 'drafts';
      r = await fetch(`${BASE}/inboxes/${ib}/${path}`, { method: 'POST', headers: H, body: JSON.stringify({ to: [to], subject, text }) });
    } else {
      return res.status(400).json({ ok: false, error: 'bad_action' });
    }
    const data = await r.json().catch(() => ({}));
    return res.status(r.ok ? 200 : r.status).json({ ok: r.ok, status: r.status, data });
  } catch (e) {
    return res.status(502).json({ ok: false, error: 'upstream_unreachable' });
  }
};
