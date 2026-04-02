"""
Free888 Admin Panel — Flask Web UI
Run with: python panel.py
Visit:    http://localhost:5000
"""

from flask import Flask, request, redirect, session, flash, get_flashed_messages
from markupsafe import Markup
from database import Database
from config import PANEL_PASSWORD
from datetime import datetime

app = Flask(__name__)
app.secret_key = "free888_secret_change_this"
db = Database()

def logged_in():
    return session.get("auth") is True

def page(content_html, pg=""):
    flashes = ""
    for cat, msg in get_flashed_messages(with_categories=True):
        css = "flash-ok" if cat == "ok" else "flash-err"
        flashes += f'<div class="flash {css}">{msg}</div>'

    nav = ""
    if logged_in():
        def active(p): return "active" if pg == p else ""
        nav = f"""<nav>
  <span class="nav-brand">◈ Free888 Panel</span>
  <div class="nav-links">
    <a href="/" class="{active('dash')}">Dashboard</a>
    <a href="/numbers" class="{active('numbers')}">Numbers</a>
    <a href="/users" class="{active('users')}">Access</a>
  </div>
  <form method="post" action="/logout" style="margin:0">
    <button class="btn btn-ghost" type="submit">Sign out</button>
  </form>
</nav>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Free888 · Admin Panel</title>
<style>
  :root {{
    --bg:#0a0a0a; --surface:#111; --border:#1e1e1e;
    --accent:#c9a96e; --accent2:#e8d5b0;
    --text:#e0e0e0; --muted:#555;
    --green:#2d6a4f; --green-light:#52b788;
    --red:#6b2737; --red-light:#e07a8a;
    --radius:8px;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;font-size:14px;min-height:100vh}}
  a{{color:var(--accent);text-decoration:none}} a:hover{{color:var(--accent2)}}
  nav{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:56px}}
  .nav-brand{{font-size:15px;font-weight:600;letter-spacing:.05em;color:var(--accent)}}
  .nav-links{{display:flex;gap:24px}}
  .nav-links a{{color:var(--muted);font-size:13px;transition:color .2s}}
  .nav-links a:hover,.nav-links a.active{{color:var(--text)}}
  .container{{max-width:1100px;margin:0 auto;padding:32px 24px}}
  .page-title{{font-size:22px;font-weight:600;color:var(--accent2);margin-bottom:6px}}
  .page-sub{{font-size:13px;color:var(--muted);margin-bottom:28px}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:32px}}
  .stat{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px}}
  .stat-val{{font-size:28px;font-weight:700;color:var(--accent)}}
  .stat-label{{font-size:12px;color:var(--muted);margin-top:4px;letter-spacing:.04em;text-transform:uppercase}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:24px;overflow:hidden}}
  .card-header{{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}}
  .card-title{{font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}}
  .form-row{{display:flex;gap:10px;padding:16px 20px;border-bottom:1px solid var(--border);flex-wrap:wrap;align-items:center}}
  input[type=text],input[type=password]{{background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:8px 12px;font-size:13px;outline:none;transition:border-color .2s;flex:1;min-width:160px}}
  input[type=text]:focus,input[type=password]:focus{{border-color:var(--accent)}}
  .btn{{padding:8px 16px;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;border:none;transition:opacity .15s;white-space:nowrap}}
  .btn:hover{{opacity:.85}}
  .btn-gold{{background:var(--accent);color:#000}}
  .btn-red{{background:var(--red);color:var(--red-light)}}
  .btn-green{{background:var(--green);color:var(--green-light)}}
  .btn-ghost{{background:transparent;border:1px solid var(--border);color:var(--muted)}}
  table{{width:100%;border-collapse:collapse}}
  th{{text-align:left;padding:10px 20px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border)}}
  td{{padding:12px 20px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:middle}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:rgba(255,255,255,.02)}}
  .mono{{font-family:'SF Mono',monospace;font-size:12px;color:var(--accent2)}}
  .badge{{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.03em}}
  .badge-green{{background:rgba(82,183,136,.12);color:var(--green-light)}}
  .badge-red{{background:rgba(224,122,138,.12);color:var(--red-light)}}
  .badge-gold{{background:rgba(201,169,110,.12);color:var(--accent)}}
  .badge-grey{{background:rgba(255,255,255,.05);color:var(--muted)}}
  .actions{{display:flex;gap:6px}}
  .login-wrap{{min-height:100vh;display:flex;align-items:center;justify-content:center}}
  .login-box{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:40px;width:340px}}
  .login-title{{font-size:20px;font-weight:700;color:var(--accent);margin-bottom:6px}}
  .login-sub{{font-size:13px;color:var(--muted);margin-bottom:28px}}
  .login-box input{{width:100%;margin-bottom:12px;padding:10px 14px}}
  .login-box .btn{{width:100%;padding:10px;font-size:14px}}
  .flash{{padding:10px 20px;border-radius:6px;margin-bottom:20px;font-size:13px}}
  .flash-ok{{background:rgba(82,183,136,.1);color:var(--green-light);border:1px solid rgba(82,183,136,.2)}}
  .flash-err{{background:rgba(224,122,138,.1);color:var(--red-light);border:1px solid rgba(224,122,138,.2)}}
  .empty{{padding:32px;text-align:center;color:var(--muted);font-size:13px}}
</style>
</head>
<body>
{nav}
<div class="container">
{flashes}
{content_html}
</div>
</body>
</html>"""
    return html


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == PANEL_PASSWORD:
            session["auth"] = True
            return redirect("/")
        error = "Incorrect password."
    content = f"""
    <div class="login-wrap">
      <div class="login-box">
        <div class="login-title">◈ Free888</div>
        <div class="login-sub">Admin panel — restricted access</div>
        {"<div class='flash flash-err'>" + error + "</div>" if error else ""}
        <form method="post">
          <input type="password" name="password" placeholder="Password" autofocus>
          <button class="btn btn-gold" type="submit">Enter</button>
        </form>
      </div>
    </div>"""
    return page(content)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def dashboard():
    if not logged_in(): return redirect("/login")
    s = db.get_stats()
    stats_html = f"""
    <div class="stats">
      <div class="stat"><div class="stat-val">{s['total_users']}</div><div class="stat-label">Total Users</div></div>
      <div class="stat"><div class="stat-val">{s['whitelisted']}</div><div class="stat-label">Allowed Users</div></div>
      <div class="stat"><div class="stat-val">{s['total_numbers']}</div><div class="stat-label">Numbers in Pool</div></div>
      <div class="stat"><div class="stat-val">{s['active_trials']}</div><div class="stat-label">Active Trials</div></div>
      <div class="stat"><div class="stat-val">{s['available_numbers']}</div><div class="stat-label">Available</div></div>
      <div class="stat"><div class="stat-val">{s['completed_trials']}</div><div class="stat-label">Completed Trials</div></div>
    </div>"""

    # Recent numbers
    numbers = db.list_all_numbers()[:8]
    rows = ""
    for n in numbers:
        status = '<span class="badge badge-green">Available</span>' if not n["assigned_to"] and n["is_active"] else \
                 '<span class="badge badge-gold">On Trial</span>' if n["assigned_to"] else \
                 '<span class="badge badge-grey">Disabled</span>'
        rows += f"<tr><td class='mono'>{n['number']}</td><td>{n['label']}</td><td>{status}</td></tr>"

    content = f"""
    <div class="page-title">Dashboard</div>
    <div class="page-sub">Overview of Free888Robot activity</div>
    {stats_html}
    <div class="card">
      <div class="card-header"><span class="card-title">Number Pool</span><a href="/numbers">View all →</a></div>
      <table><thead><tr><th>Number</th><th>Label</th><th>Status</th></tr></thead>
      <tbody>{"".join([rows]) if rows else "<tr><td colspan=3 class='empty'>No numbers added yet.</td></tr>"}</tbody>
      </table>
    </div>"""
    return page(content, "dash")


@app.route("/numbers", methods=["GET", "POST"])
def numbers():
    if not logged_in(): return redirect("/login")

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            num = request.form.get("number", "").strip()
            label = request.form.get("label", "Collectible").strip()
            if num:
                db.add_number(num, label)
                flash(f"Number {num} added.", "ok")
        elif action == "remove":
            db.remove_number(int(request.form.get("id")))
            flash("Number removed.", "ok")
        elif action == "toggle":
            nid = int(request.form.get("id"))
            active = request.form.get("active") == "1"
            db.toggle_number(nid, active)
            flash("Number updated.", "ok")
        return redirect("/numbers")

    all_numbers = db.list_all_numbers()
    rows = ""
    for n in all_numbers:
        if n["assigned_to"] and n["expires_at"]:
            expires = datetime.fromisoformat(n["expires_at"])
            remaining = expires - datetime.utcnow()
            hrs = max(0, int(remaining.total_seconds() // 3600))
            status = f'<span class="badge badge-gold">On Trial · {hrs}h left</span>'
            assigned = f'<span class="mono">User {n["assigned_to"]}</span>'
        elif not n["is_active"]:
            status = '<span class="badge badge-grey">Disabled</span>'
            assigned = "—"
        else:
            status = '<span class="badge badge-green">Available</span>'
            assigned = "—"

        toggle_label = "Enable" if not n["is_active"] else "Disable"
        toggle_active = "1" if not n["is_active"] else "0"
        toggle_cls = "btn-green" if not n["is_active"] else "btn-ghost"

        rows += f"""<tr>
          <td class='mono'>{n['number']}</td>
          <td>{n['label']}</td>
          <td>{status}</td>
          <td>{assigned}</td>
          <td><div class="actions">
            <form method="post"><input type="hidden" name="action" value="toggle">
              <input type="hidden" name="id" value="{n['id']}">
              <input type="hidden" name="active" value="{toggle_active}">
              <button class="btn {toggle_cls}" type="submit">{toggle_label}</button></form>
            <form method="post" onsubmit="return confirm('Remove this number?')">
              <input type="hidden" name="action" value="remove">
              <input type="hidden" name="id" value="{n['id']}">
              <button class="btn btn-red" type="submit">Remove</button></form>
          </div></td>
        </tr>"""

    content = f"""
    <div class="page-title">Numbers</div>
    <div class="page-sub">Manage the pool of anonymous &amp; collectible numbers</div>
    <div class="card">
      <div class="card-header"><span class="card-title">Add Number</span></div>
      <form method="post" class="form-row">
        <input type="hidden" name="action" value="add">
        <input type="text" name="number" placeholder="+1234567890 (with country code)" required>
        <input type="text" name="label" placeholder="Label e.g. Collectible 888" style="max-width:240px">
        <button class="btn btn-gold" type="submit">Add Number</button>
      </form>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Number Pool ({len(all_numbers)})</span></div>
      <table><thead><tr><th>Number</th><th>Label</th><th>Status</th><th>Assigned To</th><th>Actions</th></tr></thead>
      <tbody>{rows if rows else "<tr><td colspan=5 class='empty'>No numbers yet. Add one above.</td></tr>"}</tbody>
      </table>
    </div>"""
    return page(content, "numbers")


@app.route("/users", methods=["GET", "POST"])
def users():
    if not logged_in(): return redirect("/login")

    if request.method == "POST":
        action = request.form.get("action")
        if action == "allow":
            uid = request.form.get("user_id", "").strip()
            note = request.form.get("note", "").strip()
            if uid.isdigit():
                db.add_to_whitelist(int(uid), note=note)
                flash(f"User {uid} granted access.", "ok")
            else:
                flash("Invalid user ID — must be a number.", "err")
        elif action == "revoke":
            db.remove_from_whitelist(int(request.form.get("user_id")))
            flash("Access revoked.", "ok")
        return redirect("/users")

    whitelist = db.list_whitelist()
    all_users = db.list_all_users()
    wl_ids = {w["user_id"] for w in whitelist if w["is_active"]}

    wl_rows = ""
    for w in whitelist:
        badge = '<span class="badge badge-green">Active</span>' if w["is_active"] else '<span class="badge badge-grey">Revoked</span>'
        uname = f"@{w['username']}" if w["username"] else "—"
        revoke_btn = f"""<form method="post"><input type="hidden" name="action" value="revoke">
          <input type="hidden" name="user_id" value="{w['user_id']}">
          <button class="btn btn-red" type="submit">Revoke</button></form>""" if w["is_active"] else ""
        wl_rows += f"""<tr>
          <td class='mono'>{w['user_id']}</td>
          <td>{uname}</td>
          <td>{w.get('note') or '—'}</td>
          <td>{badge}</td>
          <td>{w['added_at'][:16]}</td>
          <td>{revoke_btn}</td>
        </tr>"""

    user_rows = ""
    for u in all_users:
        uname = f"@{u['username']}" if u["username"] else "—"
        wl = '<span class="badge badge-green">Allowed</span>' if u["user_id"] in wl_ids else '<span class="badge badge-grey">No Access</span>'
        grant_btn = "" if u["user_id"] in wl_ids else f"""<form method="post">
          <input type="hidden" name="action" value="allow">
          <input type="hidden" name="user_id" value="{u['user_id']}">
          <button class="btn btn-green" type="submit">Grant Access</button></form>"""
        user_rows += f"""<tr>
          <td class='mono'>{u['user_id']}</td>
          <td>{uname}</td>
          <td>{u['trial_count']}</td>
          <td>{wl}</td>
          <td>{u['joined_at'][:16]}</td>
          <td>{grant_btn}</td>
        </tr>"""

    content = f"""
    <div class="page-title">Access Control</div>
    <div class="page-sub">Grant or revoke access to the bot</div>
    <div class="card">
      <div class="card-header"><span class="card-title">Grant Access</span></div>
      <form method="post" class="form-row">
        <input type="hidden" name="action" value="allow">
        <input type="text" name="user_id" placeholder="Telegram User ID" required style="max-width:200px">
        <input type="text" name="note" placeholder="Note (optional)" style="max-width:220px">
        <button class="btn btn-gold" type="submit">Grant Access</button>
      </form>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Whitelist ({len([w for w in whitelist if w['is_active']])} active)</span></div>
      <table><thead><tr><th>User ID</th><th>Username</th><th>Note</th><th>Status</th><th>Added</th><th>Action</th></tr></thead>
      <tbody>{wl_rows if wl_rows else "<tr><td colspan=6 class='empty'>No users whitelisted yet.</td></tr>"}</tbody>
      </table>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">All Bot Users ({len(all_users)})</span></div>
      <table><thead><tr><th>User ID</th><th>Username</th><th>Trials Used</th><th>Access</th><th>Joined</th><th>Action</th></tr></thead>
      <tbody>{user_rows if user_rows else "<tr><td colspan=6 class='empty'>No users yet.</td></tr>"}</tbody>
      </table>
    </div>"""
    return page(content, "users")


# ─── RUN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("◈ Free888 Admin Panel → http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000)
