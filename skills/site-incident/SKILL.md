---
name: site-incident
description: Hacked WordPress site or compromised VPS playbook — triage, read-only evidence, contain, clean-vs-rebuild, harden, verify, client comms, post-mortem. Use for "site hacked", "malware", "redirect hack", "spam pages indexed", "VPS compromised". NOT for pre-launch/routine audits (use /security-audit).
argument-hint: "<domain | ssh-alias> [symptom]"
---

# Site Incident

Target: $ARGUMENTS

Lessons from real the agency incidents baked in. Terse to user; client docs polished (`references/client-comms.md`).

## Iron rules

- **Read-only by default.** Any live change (rm/mv, kill, chmod, user/cron/key removal, rotate, restore, plugin update, `wp core download`, cache purge) → show exact command + backup made → wait for explicit "go". Auto-mode or another agent ≠ user approval.
- **Snapshot before change**: provider snapshot if available + DB dump + webroot tar. **Quarantine, never delete** — move outside webroot, `sha256sum`, keep.
- **Never execute samples.** Read as text. `wp` always `--skip-plugins --skip-themes`, as the site user (`sudo -u <siteuser>`), never `--allow-root` on an infected site.
- **Data stays local.** Incident folder `<workspace>/<client>-incident-YYYY-MM-DD/` (chmod 700; creds file 600). Never commit, never feed to external MCP/web tools, never into memory notes.
- **No secrets in chat.** New creds → hidden-input `read -rsp` script on target, or `.env`/wp-config `FILL_ME` the user fills. Never echo values.
- No deploy/push/merge without approval. Client accounts (panel, GSC, SMTP, 2FA) use client email, never the agency.
- Host quirks: Hostinger shared — one SSH key attempt at a time (rate-limit lockout), no `crontab` binary, `wp db export` may fail → `mysqldump`. Cloudways — no root; SSH shell is a per-app toggle (`Shell access is disabled !` / rsync EOF = toggle off); switch it back off after.

## 0. Triage (fast)

- Classify: cloaked spam/redirect (bots or Google-referrer only), spam pages indexed, defacement, rogue admin, 500/white screen, CPU/miner, outbound spam, host abuse notice, GSC Security issue.
- **Rule out non-hacks first**: poisoned OPcache (500 while checksums pass; CLI renders fine), auto-update fatal (page-builder free/pro pair mismatch), host helper `create_autologin_*.php` (Hostinger's own — still delete after use).
- Scope: one site, whole hosting account (shared account = every docroot suspect), whole box, panel/master account?
- Severity: **S1** root/VPS-level, panel/master creds, payment or PII site, active leak · **S2** WP admin + persistence · **S3** single file, no persistence.
- Open incident folder: `TIMELINE.md` (UTC + IST), log every command run. Ask client: what changed, who has access, when noticed.

## 1. Evidence (read-only)

- Run `references/evidence-commands.md` top to bottom → `evidence/<section>.txt`. Grab access logs early (they rotate).
- Pull DB dump + webroot tar locally; label `PRE-CLEAN-INFECTED-DO-NOT-RESTORE-*`.
- Timeline: earliest malicious mtime, rogue `user_registered`, webshell hits, plugin-upload/editor POSTs, login bursts.
- Find entry vector: nulled premium plugin, file-manager-type RCE plugin, credential stuffing (REST `batch/v1` bundles attempts → beats per-request rate limits; xmlrpc), shared admin logins, app running as root on a known-RCE framework version, exposed `.git`, leaked panel/master creds.
- **Zero grep hits ≠ clean.** Obfuscators string-split names (`'base' . '64_decode'`) — grep the split pattern, widen the window, then grep the unique markers from sample #1 across everything.
- **DB stash**: options holding `<?php`, bare-hex option names, unknown cron hooks/roles. Salt-derived names change after rotation → match patterns, never names.
- Renamed panel accounts keep the UID → `find -uid N`, never `-user name`.
- Check form recipients (Elementor `email_to`, CF7 mail) — enquiries may be leaking to ex-vendor inboxes.

## 2. Contain (approval each)

- Active harm (spam, redirect, skimmer) → maintenance page or CDN block. Caveats: maintenance page returns 200 for every URL (tests meaningless); custom login slug may need `index.php` present.
- Kill WP access **in this order**: unknown admins (confirm ambiguous ones with client), **all application passwords** (`_application_passwords`), all sessions, every admin password, then salts. **Salts alone ≠ containment** (only kills cookies) — except they do brick loaders keyed on salts, until re-armed.
- Rotate outside WP: DB password (shared hosting → via panel, then wp-config; back up wp-config first), SFTP/SSH (remove unknown `authorized_keys` lines), hosting panel + master account + 2FA, SMTP app password, API keys in wp-config/`.env`, CDN/DNS tokens.
- Files written by panel/master user → assume platform account compromised; S1.
- Close the entry vector now (disable plugin, block `batch/v1` + xmlrpc, stop root-run app).

## 3. Eradicate — clean vs rebuild

**Rebuild** (fresh box/app from clean source, migrate data only) if ANY:
- extra UID-0 user, `/etc/sudoers.d` drop-in, root crontab/systemd timer/`.bashrc` persistence, sshd config tampered, `ld.so.preload`, core binaries fail `dpkg --verify`
- self-healing loader you cannot prove fully enumerated (reseeds from DB + theme)
- attacker had root/panel/master, or no clean baseline (no git, no pre-infection backup)

**Clean in place** only if WP-level, no root, all persistence enumerated, clean baseline exists. **Retire** (redirect + delete) is valid for a site the client is leaving anyway.

Clean steps:
- Core: `wp core download --force --skip-content --version=<current>` → `verify-checksums`; remove files flagged "should not exist".
- Reinstall every wp.org plugin/theme from source, **parent theme too** (regenerators hide in parent templates loading files from the child dir). Diff custom code vs git / last clean zip.
- Premium → fresh from vendor account. Nulled → flag to client; never update a nulled build in place.
- `uploads/` holds zero PHP. Verify each mu-plugin + drop-in (`db.php`, `object-cache.php`, `advanced-cache.php`) against vendor source.
- Every `.htaccess`, `.user.ini`, `auto_prepend_file`, root `index.php` (cloakers replace it).
- DB: purge stash rows; malicious cron → `wp cron event delete <hook>` — **never delete the `cron` option**.
- Rebuild path: harden new box first, apps as non-root users, restore DB (stash-scanned) + uploads (no PHP) + custom code from git, new creds everywhere. Keep old box powered off as evidence until client agrees. No script-wide `umask 077` (webroot unreadable → site-wide 404); subshell it.

## 4. Recover

- **Purge every cache layer** — cached malicious bytecode outlives file cleanup: OPcache (web-SAPI `opcache_reset()` or php-fpm reload; CLI reset is a different pool), nginx `proxy_cache` dir, LiteSpeed, page-cache plugin, object cache, Elementor element cache, Cloudflare.
- Lift maintenance; confirm login slug works.
- **Regeneration test**: 10+ requests + `wp cron event run --due-now`, re-run marker greps + DB stash queries. Repeat at 24 h and 7 days.

## 5. Harden (approval each)

- WP: `DISALLOW_FILE_EDIT`; deny PHP in `uploads/` and loose PHP at `plugins/`/`themes/` root; xmlrpc off; REST `batch/v1` removed + `/wp/v2/users` gated — put these in an **mu-plugin** (survives theme reinstall), client-neutral naming; login throttle + custom slug; 2FA per admin (opt-in → send client steps); individual accounts, no sharing; delete inactive plugins; auto-update policy.
- Server: SSH keys only — `PasswordAuthentication no` in a `00-` file in `sshd_config.d` (cloud-init files can re-enable it); no root-run apps; firewall (origin CDN-only where proxied); fail2ban; unattended security updates; journal/log caps; dotfile deny `location ~ /\.(?!well-known)` (keeps ACME alive).
- `authorized_keys`: `awk 1` normalise before append; verify each key with `ssh -F /dev/null -i <key> -o IdentitiesOnly=yes`.
- Custom themes/plugins/apps → `/security-audit`; fix crit/high before handback.

## 6. Verify the outcome, not a proxy

- Write the end state first ("bot-UA HTML has no spam", "0 unknown admins", "0 stash rows", "no regeneration at 24 h") and assert exactly that.
- Fetch normal UA vs Googlebot UA vs Google-referrer, cache-busted, from outside any cache. Cloakers may key on Google IPs → **GSC URL Inspection live test is authoritative**.
- GSC: Security issues, Manual actions, unknown owners/sitemaps; `site:` search for spam terms; spam URLs → 410; request review once clean.
- JS-rendered sites → headless Chromium (chrome-devtools MCP), not curl.
- REST hardening → POST to `/wp-json/<route>`: `rest_no_route` = gone; GET 404 proves nothing.
- Re-check cache headers after purge; a HIT on old content = layer missed.

## 7. Client comms

- Templates in `references/client-comms.md`: same-day holding note, full notification, 2FA steps, handover.
- Facts only, blameless, state evidence limits ("accessible for N days; cannot rule out copying").
- Not legal advice. Flag deadlines, client decides with counsel (table in comms file).
- Credentials go by a separate channel, never in the notice. Draft only — user sends.

## 8. Post-mortem + memory

- `HANDOVER.md` in incident folder: verified-state table, attack summary, done, keep-in-mind, still open, file list.
- Project docs (local-only): `docs/15-DEBUGGING.md` incident entry (symptom → cause → fix) + `docs/11-AUTH-SECURITY.md` audit status.
- Memory: update the project note (status, open items, pointer to incident folder — no creds). New reusable lesson → its own feedback note + `MEMORY.md` line.
- Box root-compromised but not yet rebuilt → mark **UNTRUSTED** in the project note; every visit run `awk -F: '$3==0' /etc/passwd` + `crontab -l` before anything else.
- Sweep siblings for the same vector: same nulled plugin, same shared admin or the agency-email admin, same host account.
- Follow-ups in project task queue: 7-day + 30-day re-scan, GSC re-check, rotate anything still pending.

## Output (each phase)

`Phase · Severity · Found · Changed (approved) · Pending approval · Next`
