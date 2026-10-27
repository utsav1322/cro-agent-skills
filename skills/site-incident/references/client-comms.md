# Client communication templates

Internal rules (do not send this section):

- Drafts only. The account owner reviews and sends. Save each as its own file in the incident folder.
- Facts, not speculation. Blameless: describe systems and access, never individuals.
- State the limits of the evidence plainly. Never write "no data was taken" — write what the logs do and do not show.
- No credentials, login slugs or reset links in any of these documents. Send those by a separate channel.
- Not legal advice. Flag possible obligations; the client decides with its own counsel.
- Client accounts (hosting, GSC, SMTP, 2FA) must use the client's own email address.
- Replace every `{{placeholder}}`. Delete any section that does not apply.

---

## 1. Same-day holding note

**Subject:** Security issue on {{domain}} — we are on it

Hi {{first name}},

This morning we identified a security issue affecting {{domain}}. {{One sentence on what was observed, e.g. "Some visitors arriving from Google were being redirected to an unrelated website."}}

We have already {{taken the site into maintenance mode / blocked the affected pages / secured the administrator accounts}} to stop any further impact, and we have preserved a full copy of the site and its logs so we can establish exactly what happened.

There are two things we need from you today:

1. {{e.g. Please change the password for your hosting account at {{provider}} and turn on two-factor authentication.}}
2. {{e.g. Please confirm whether you recognise the user account "{{username}}".}}

Please do not make changes to the website in the meantime, as this can destroy evidence we need. We will send you a full written report by {{date/time}}. If you have any questions before then, call me directly on {{phone}}.

Regards,
{{name}}
{{company}}

---

## 2. Incident notification (full report)

# Security incident — {{domain}}

**Prepared for {{client legal name}} — {{date}}**

> This report sets out the technical facts as we have established them. It is not legal advice. Decisions about notification obligations rest with {{client}}, ideally with its privacy adviser or legal counsel.

### Summary

Between **{{start date}}** and **{{containment date}}**, an unauthorised party had {{administrator-level access to the website / access to the server hosting the website}}. {{One or two sentences on what they did, e.g. "They installed software that allowed them to log in without a password and to publish spam pages that were shown only to search engines."}}

The unauthorised access has been stopped, the malicious software has been removed and verified gone, and all relevant passwords have been changed. {{The site is live again / The site remains offline pending the steps below.}}

### How it happened

{{Plain-language description of the entry vector. Examples:}}
- {{"The attacker did not exploit a software flaw. They logged in with a working administrator username and password, after an automated password-guessing campaign that began on {{date}}."}}
- {{"An outdated plugin, {{name}}, contained a known vulnerability that allowed files to be uploaded without logging in."}}
- {{"An application on the same server was running a version with a publicly known remote-code-execution flaw, which gave the attacker control of the whole server."}}

| Date and time ({{timezone}}) | Event |
|---|---|
| {{date}} | {{First evidence of attack activity}} |
| {{date}} | {{Access gained}} |
| {{date}} | {{Malicious software installed / accounts created}} |
| {{date}} | {{Issue detected}} |
| {{date}} | {{Access removed and site secured}} |

### What the attacker could reach

{{Administrator / server-level}} access means access to everything the website stores. In this case that includes:

| Data | Volume |
|---|---|
| {{Enquiry form submissions}} | {{n}} |
| {{Customer accounts}} | {{n}} |
| {{Orders (names, addresses, phone numbers; no card details are stored on the site)}} | {{n}} |

We have counted these records but **have not read their contents**. We recommend {{client}} review them to establish exactly what personal information is involved.

### Was data actually taken?

{{We found no evidence that data was copied or exported in bulk.}} We examined the server access logs for the full period and found {{no large transfers to the attacker's addresses and no requests to export or download endpoints}}.

However, absence of evidence is not proof:

- An administrator can read records page by page in the normal admin screens, which looks the same as ordinary use in the logs.
- {{Malicious software / server-level access}} could read the database directly, which does not appear in web logs at all.
- {{Logs do not cover the full period at the same level of detail.}}

The accurate position is: **the data was accessible for approximately {{n}} days, and we cannot rule out that it was viewed or copied.**

### What has been done

- All malicious files identified, removed and preserved for investigation
- All unauthorised user accounts removed
- All administrator passwords changed, all active sessions ended, and all application access keys revoked
- {{Database, hosting and email passwords changed}}
- {{The site was rebuilt from clean sources on a new server}} / {{WordPress, themes and plugins were reinstalled from official sources}}
- The method used to gain access has been closed
- Additional protections added: {{login attempt limits, private login address, two-factor authentication available, file editing disabled, script execution blocked in upload folders, unused plugins removed}}
- {{Search engines: spam pages removed and Google asked to review the site}}
- A full copy of the site, database and logs has been retained as evidence

### What we need you to do

1. {{**Today:** change your hosting account password and enable two-factor authentication. Until this is done the site could be compromised again regardless of the work above.}}
2. Set up two-factor authentication for every administrator (instructions attached).
3. {{Confirm whether the following accounts should exist: …}}
4. {{Purchase genuine licences for the premium plugins in use. Unlicensed copies from unofficial sources are a common cause of this kind of compromise.}}
5. Review who holds administrator access. Each person should have their own account; shared logins should be retired.
6. Seek advice on any notification obligations (see below).

### Possible notification obligations

Depending on where {{client}} operates and whose data was involved, notification duties may apply. We list these so advice can be sought promptly, not as a conclusion:

{{Keep only the rows that apply — and verify each against current rules before sending.}}

| Regime | What may be required | Timing |
|---|---|---|
| India — CERT-In Directions (2022) | Report specified cyber incidents, including website compromise and unauthorised access, to CERT-In | Within 6 hours of noticing |
| India — DPDP Act 2023 and Rules | Inform the Data Protection Board and affected individuals of a personal data breach | Check whether the breach provisions are in force on the incident date |
| Australia — Notifiable Data Breaches scheme | Assess a suspected breach; notify the OAIC and affected individuals if serious harm is likely | Assessment within 30 days |
| EU / UK GDPR | Notify the supervisory authority; individuals if high risk | Within 72 hours of becoming aware |
| UAE and other jurisdictions | Federal, DIFC or ADGM data-protection rules may apply | Seek advice |
| Payment cards | Inform the payment provider / acquirer if card data may be involved | Promptly |
| Cyber insurance / contracts | Policies and customer contracts often carry notice conditions | Check the policy |

The relevant start date for these assessments is **{{start date}}**, when unauthorised access began.

### Evidence retained

Malicious file samples with SHA-256 hashes, a pre-cleanup copy of the database (forensic only — never to be restored), and server access logs covering {{period}}. Held securely by {{company}} and available to {{client}}'s advisers on request.

**Prepared by:** {{name}}, {{company}}
**Contact:** {{phone}} · {{email}}

---

## 3. Two-factor authentication — steps for administrators

# Setting up two-factor authentication — {{domain}}

Two-factor authentication (2FA) means that even if someone learns your password, they still cannot log in without your phone. It is the single most effective protection against what happened. **Every administrator needs to do this on their own account.** It takes about three minutes.

### Before you start

- A smartphone with a free authenticator app: **Google Authenticator**, **Microsoft Authenticator** or **Authy**.
- Your login details, which have been **sent to you separately**.

> The login address is no longer the standard `/wp-login.php`; it has moved to a private address. Use the address supplied with your login details. The old address now shows "Page not found" — that is expected.

### Steps

1. **Log in** using the private login address.
2. **Open your profile**: hover over *"Howdy, [your name]"* in the top-right corner and choose **Edit Profile** (or **Users → Profile** in the left menu).
3. **Scroll to the two-factor authentication section** {{exact section name for the plugin in use}}.
4. **Turn it on.** A QR code (a square black-and-white barcode) appears.
5. **In your authenticator app**, add a new account and choose **Scan a QR code**.
6. **Point your phone's camera at the QR code.** The app adds an entry for {{site name}} showing a **6-digit code that changes every 30 seconds**.
7. **Type the current code** into the confirmation box on the website and save. If it is rejected, wait for the next code and try again.
8. **Save your backup codes.** This is the most important step. Print them or store them in a password manager — somewhere that is not your phone. Without them, losing your phone means losing access to the website.

### From now on

Log in with your username and password as usual, then enter the current 6-digit code from the app.

### If something goes wrong

- **The code is rejected but looks right:** the code is time-based, so set your phone's date and time to automatic.
- **You lost your phone:** log in with one backup code (each works once), then set 2FA up again on the new phone.
- **You lost your phone and your backup codes:** contact {{support contact}}. We can reset 2FA on your account after verifying your identity.

### Please also

- **Never share your login**, including with colleagues or agencies. Anyone who needs access should be given their own account.
- **Use a password you use nowhere else.** A password reused on another site that is breached puts this one at risk too.

---

## 4. Handover — outline (`HANDOVER.md`)

# {{Client}} ({{domain}}) — incident handover

**{{date}}.** One line: compromised → cleaned / rebuilt → verified → hardened → current status.

### Current verified state

| Check | Result |
|---|---|
| Malware markers in files | {{0}} |
| Malicious rows in database | {{0}} |
| Unknown admins / application passwords / sessions | {{0 / 0 / 0}} |
| mu-plugins and drop-ins | {{only expected, each verified}} |
| Server: extra UID-0 users, unknown cron/timers/keys | {{none}} (VPS only) |
| Regeneration after requests + cron, re-checked at 24 h | {{none}} |
| Bot vs normal user-agent HTML | {{identical, clean}} |
| GSC Security issues / Manual actions | {{none / review requested on …}} |
| Frontend | {{n/n pages 200}} · PHP fatals {{0}} |
| Site status | {{LIVE, indexable}} |

### What the attack was
Entry vector, persistence mechanisms, malware families (behaviour only — no samples), timeline in brief.

### What was done
- **Cleanup** — files quarantined (where), core/plugins/themes reinstalled from source, database rows purged, accounts removed
- **Credentials** — what was rotated, and by whom (no values)
- **Hardening** — each control and where it lives (mu-plugin, `.htaccess`, server config, host panel)

### What to keep in mind
Gotchas the next person will hit: frozen or held-back plugins and why, legitimate files that look suspicious, false-pass traps (maintenance page, GET vs POST tests), cache layers to purge, the re-infection check commands.

### Never restore
The `PRE-CLEAN-INFECTED-*` database dump — forensic only. Name the clean restore point.

### Still open
Numbered, with owner and due date. Client notification and 2FA enrolment always appear here until confirmed.

### Files in this folder
One line per file. Credentials file: chmod 600, local only, never shared in this document.
