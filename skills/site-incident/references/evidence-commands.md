# Evidence commands (read-only unless marked ⚠)

Run non-interactively and save locally: `ssh <alias> '<cmd>' > evidence/<section>.txt 2>&1`.
Sections 1–6 need root (VPS). Shared hosting / Cloudways (no root): skip to §7.
Every ⚠ command writes to the live server → show it, get explicit "go", back up first.

```bash
WEB=/path/to/webroot            # CloudPanel /home/<u>/htdocs/<domain> · Hostinger ~/domains/<d>/public_html · Cloudways ~/public_html
SITEUSER=<site-user>
D=https://example.com           # live site URL
WP="sudo -u $SITEUSER -- wp --path=$WEB --skip-plugins --skip-themes"   # shared hosting: drop the sudo part
WPFULL="sudo -u $SITEUSER -- wp --path=$WEB"                            # plugins loaded — post-clean only
P=$($WP db prefix)              # table prefix — never assume wp_
date -u; hostname; uptime; id
```

`--skip-plugins --skip-themes` still executes `wp-config.php`, mu-plugins and drop-ins. `wp db query` loads only `wp-config.php` — prefer it for DB evidence. If wp-config itself is suspect, read it as text first. `wp db *` needs `proc_open`; where disabled (Hostinger shared) use the `mysql` client.

## 1. Accounts (VPS)

```bash
awk -F: '$3==0' /etc/passwd                      # must be root ONLY — anything else = rebuild
awk -F: '$3>=1000 && $3<65534 {print $1,$3,$6,$7}' /etc/passwd
awk -F: '$2==""{print "EMPTY PW:",$1}' /etc/shadow
getent group sudo wheel adm docker               # docker group = root-equivalent
ls -la /etc/sudoers.d/; grep -rhv '^\s*\(#\|$\)' /etc/sudoers /etc/sudoers.d/
last -Faiw | head -50; lastb -Fai 2>/dev/null | head -20
zgrep -hE 'Accepted|Invalid user|Failed password' /var/log/auth.log* /var/log/secure* 2>/dev/null | tail -200
journalctl -u ssh -u sshd --since '30 days ago' --no-pager | grep -E 'Accepted|Invalid' | tail -100
```

## 2. SSH

```bash
for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
  [ -f "$f" ] || continue; echo "== $f"; stat -c '%y %U' "$f"
  ssh-keygen -lf "$f"; echo "non-empty lines: $(grep -c . "$f")"   # count mismatch = glued/odd line
done
ls -la /etc/ssh/sshd_config.d/; grep -rn . /etc/ssh/sshd_config.d/
sshd -T | grep -Ei '^(passwordauthentication|permitrootlogin|pubkeyauthentication|authorizedkeysfile|kbdinteractiveauthentication)'
```

## 3. Persistence

```bash
for u in $(cut -d: -f1 /etc/passwd); do c=$(crontab -l -u "$u" 2>/dev/null) && printf '== %s\n%s\n' "$u" "$c"; done
cat /etc/crontab; ls -la /etc/cron.d /etc/cron.hourly /etc/cron.daily /var/spool/cron/crontabs 2>/dev/null
systemctl list-timers --all --no-pager
systemctl list-unit-files --state=enabled --no-pager
find /etc/systemd/system /lib/systemd/system /usr/lib/systemd/system -type f -mtime -90 -printf '%TY-%Tm-%Td %p\n' 2>/dev/null | sort
find /root /home -path '*/.config/systemd/user/*' -type f 2>/dev/null
cat /etc/ld.so.preload 2>/dev/null                # should not exist
ls -la /etc/rc.local /etc/init.d/ 2>/dev/null
grep -nE 'curl|wget|base64|/dev/tcp|nc |useradd|usermod|chpasswd|python3? -c' \
  /root/.bashrc /root/.profile /root/.bash_profile /home/*/.bashrc /home/*/.profile /etc/profile /etc/profile.d/* /etc/bash.bashrc 2>/dev/null
docker ps -a --format '{{.Names}}  {{.Image}}  {{.Status}}  {{.CreatedAt}}' 2>/dev/null; docker images 2>/dev/null
ps -eo user,pid,lstart,cmd | grep -Ei 'node|pm2|next|python|php' | grep -v grep   # apps running as root = finding
```

## 4. Processes + network

```bash
ps aux --sort=-%cpu | head -30
ps auxf | head -150
ls -l /proc/[0-9]*/exe 2>/dev/null | grep -E '\(deleted\)|/tmp/|/var/tmp/|/dev/shm/'   # running from deleted/temp binary
ss -tulpn                                          # listeners
ss -tnp state established                          # outbound — unknown IPs, :3333/:4444/:5555 miner pools, IRC
ls -la /tmp /var/tmp /dev/shm; find /tmp /var/tmp /dev/shm -type f -perm -u+x 2>/dev/null
```

## 5. Package integrity

```bash
dpkg --verify 2>/dev/null | grep -v ' c /'        # Debian/Ubuntu; RHEL: rpm -Va
debsums -s 2>/dev/null
```

`ps`, `ss`, `ls`, `sshd`, `login`, `netstat` failing verification → possible rootkit → stop trusting this box's output → rebuild.

## 6. Web server + PHP config

```bash
nginx -T 2>/dev/null | grep -nE 'server_name|root |proxy_cache_path|fastcgi_cache_path|include |return 30|auto_prepend'
apache2ctl -S 2>/dev/null
grep -rnE 'auto_(prepend|append)_file|php_admin_value|opcache.validate_timestamps' /etc/php/*/fpm/ 2>/dev/null
php -i | grep -Ei 'auto_prepend_file|auto_append_file|disable_functions|opcache.validate_timestamps'   # CLI ini ≠ FPM ini
find "$WEB" \( -name '.user.ini' -o -name 'php.ini' \) -exec grep -HnE 'auto_(prepend|append)' {} +
```

## 7. Files (WordPress)

```bash
cd "$WEB"
# Recent changes. mtime is forgeable; ctime is not (without root) — check both.
find . -type f -mtime -30 ! -path './wp-content/cache/*' -printf '%TY-%Tm-%Td %TH:%TM  %u  %s  %p\n' | sort | tail -200
find . -type f -ctime -30 ! -path './wp-content/cache/*' -printf '%CY-%Cm-%Cd %CH:%CM  %u  %p\n' | sort | tail -200
# Files not owned by the site user (root/panel/master writes)
find . ! -user "$SITEUSER" -printf '%u %p\n' | head -50; find . -type f -perm -o+w | head
# PHP where it never belongs
find wp-content/uploads -type f \( -iname '*.php*' -o -iname '*.phtml' -o -iname '*.phar' -o -iname '*.pht' -o -name '.htaccess' -o -name '.user.ini' \)
ls -la wp-content/mu-plugins/ wp-content/*.php     # drop-ins: db.php object-cache.php advanced-cache.php sunrise.php maintenance.php
ls -la .; wc -c index.php; head -c 600 index.php   # core index.php ≈ 400 bytes; replaced = cloaker
ls google*.html BingSiteAuth.xml 2>/dev/null       # unknown verification files = attacker-added GSC/Bing owner
find . -name .htaccess -printf '== %p\n' -exec cat {} \;   # deny-all-except-shell whitelists, rewrite-to-spam
# Signatures — noisy, triage against clean copies
grep -rlE 'eval[[:space:]]*\(|assert[[:space:]]*\(|gzinflate|gzuncompress|str_rot13|openssl_decrypt|create_function|\$_(POST|GET|REQUEST|COOKIE)\[' --include='*.php' wp-content . 2>/dev/null | sort -u | head -100
# String-split function names ('base' . '64_decode') — plain greps miss these
grep -rnoE "['\"][a-z0-9_]{1,12}['\"][[:space:]]*\.[[:space:]]*['\"][a-z0-9_]{1,12}['\"]" --include='*.php' wp-content \
  | grep -iE 'base|64|decode|inflate|tmp|file|eval|exec|system|assert|create' | head -50
grep -rlE 'goto [A-Za-z0-9_]+;' --include='*.php' wp-content | head   # goto-obfuscation
find wp-content wp-includes wp-admin -name '*.php' -exec awk 'length>3000{print FILENAME; nextfile}' {} + 2>/dev/null   # packed one-liners
grep -rlE 'HTTP_USER_AGENT.{0,120}(bot|google|bing)|HTTP_REFERER.{0,120}(google|bing)' --include='*.php' . | head   # cloaking
# Parent theme loading files from the child dir (hidden regenerator)
grep -rnE '(require|include)(_once)?[[:space:]]*\(?[[:space:]]*get_stylesheet_directory' wp-content/themes/<parent>/
# Once you have a unique marker from sample #1, sweep everything:
grep -rlE '<marker1>|<marker2>' . --include='*.php'
```

Hash every suspect before touching it: `sha256sum <files> > evidence/SHA256SUMS`.

## 8. WP-CLI

```bash
$WP core version --extra
$WP core verify-checksums                        # heavy on shared hosting — don't speed-test the site meanwhile
$WP core verify-checksums --include-root         # also flags non-core files in webroot (newer WP-CLI)
$WP plugin verify-checksums --all                # wp.org only; premium = "could not retrieve"
$WP plugin list --fields=name,status,version,update_version,auto_update
$WP theme list --fields=name,status,version,update_version
for o in siteurl home template stylesheet users_can_register default_role admin_email; do printf '%s: ' $o; $WP option get $o; done
$WP option get active_plugins --format=json
$WP user list --role=administrator --fields=ID,user_login,user_email,user_registered
$WP user list --fields=ID,user_login,user_email,roles,user_registered --orderby=user_registered --order=DESC --number=30
$WP role list
for id in $($WP user list --role=administrator --field=ID); do
  echo "== user $id"; $WP user application-password list $id --fields=uuid,name,created,last_used,last_ip; $WP user session list $id
done
$WP cron event list --fields=hook,next_run_relative,recurrence
```

## 9. Database (stash, users, content)

Avoid `REPLACE(` in read queries — `wp db query` swallows the output.

```bash
$WP db query "SELECT option_name, LENGTH(option_value) len FROM ${P}options WHERE option_value LIKE '%<?php%'"      # PHP never belongs in an option
$WP db query "SELECT option_name, LENGTH(option_value) len FROM ${P}options WHERE option_name REGEXP '^_?[0-9a-f]{16,}$'"   # WP never names options bare hex
$WP db query "SELECT option_name FROM ${P}options WHERE option_value REGEXP 'eval[(]|base64_decode|gzinflate|str_rot13' LIMIT 50"
$WP db query "SELECT option_name, LENGTH(option_value) len, autoload FROM ${P}options ORDER BY len DESC LIMIT 25"
# Admins straight from the DB (hooks can hide users from wp-admin and even wp-cli)
$WP db query "SELECT u.ID, u.user_login, u.user_email, u.user_registered FROM ${P}users u JOIN ${P}usermeta m ON m.user_id=u.ID WHERE m.meta_key='${P}capabilities' AND m.meta_value LIKE '%administrator%'"
$WP db query "SELECT ID, user_login, user_email, user_registered FROM ${P}users ORDER BY user_registered DESC LIMIT 20"
$WP db query "SELECT user_id FROM ${P}usermeta WHERE meta_key='_application_passwords'"   # every user, not just admins
$WP db query "SELECT option_value FROM ${P}options WHERE option_name='${P}user_roles'" | head -c 4000   # rogue roles/caps
$WP db query "SELECT meta_id, post_id, meta_key FROM ${P}postmeta WHERE meta_value LIKE '%<?php%' OR meta_value REGEXP 'eval[(]|atob[(]|fromCharCode' LIMIT 50"
$WP db query "SELECT ID, post_type, post_status, post_date, post_title FROM ${P}posts WHERE post_type<>'revision' AND post_content REGEXP '<script[^>]+src=|<iframe|display:[[:space:]]*none' LIMIT 50"
$WP db query "SELECT post_type, post_status, COUNT(*) FROM ${P}posts WHERE post_date > NOW() - INTERVAL 60 DAY GROUP BY 1,2"   # spam-page bursts
# Form recipients (data leaking to old vendors / unrelated inboxes)
$WP db query "SELECT meta_value FROM ${P}postmeta WHERE meta_key='_elementor_data' AND meta_value LIKE '%email_to%'" --skip-column-names \
  | grep -oE '"email_(to|from)[a-z_]*":"[^"]*"' | sort | uniq -c
$WP db query "SELECT post_id, LEFT(meta_value,400) FROM ${P}postmeta WHERE meta_key='_mail'"   # Contact Form 7
```

Never delete the `cron` option to clear an event — it holds every scheduled task.

## 10. Access logs

Paths: nginx `/var/log/nginx/` · CloudPanel `/home/<u>/logs/nginx/` · Cloudways `~/logs/` · Hostinger shared `~/logs/` or hPanel · Apache `/var/log/apache2/`.
Behind Cloudflare, `$1` is a CF edge IP unless real-IP is configured.

```bash
L='access.log*'
zgrep -hE '"POST [^"]*(wp-login\.php|xmlrpc\.php|batch/v1|/wp-json/wp/v2/users)' $L | awk '{print $1}' | sort | uniq -c | sort -rn | head -20
zgrep -hE '"(GET|POST) [^"]*\.php' $L | grep -vE 'wp-(login|cron|comments-post)\.php|/wp-admin/|/index\.php|xmlrpc\.php' \
  | awk '{print $7}' | sort | uniq -c | sort -rn | head -40          # odd PHP endpoints = webshell use
zgrep -hE 'update\.php\?action=upload-(plugin|theme)|plugin-install\.php|theme-editor\.php|plugin-editor\.php' $L | head
zgrep -hF '<suspect-file>.php' $L | head; zgrep -hF '<suspect-file>.php' $L | tail -3   # first + last use
zgrep -h 'Googlebot' $L | awk '{print $7}' | sort | uniq -c | sort -rn | head -30   # spam URL patterns Google is crawling
```

## 11. External view (from local machine)

```bash
D=https://example.com; mkdir -p evidence/ext
UA_BOT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$D/?cb=$RANDOM"
curl -s "$D/?cb=$RANDOM" > evidence/ext/normal.html
curl -s -A "$UA_BOT" "$D/?cb=$RANDOM" > evidence/ext/bot.html
curl -s -e 'https://www.google.com/' -A 'Mozilla/5.0 (Linux; Android 14) Mobile' "$D/?cb=$RANDOM" > evidence/ext/ref.html
wc -c evidence/ext/*.html; grep -ciE 'casino|slot|judi|togel|gacor|viagra|cialis|loan|porn' evidence/ext/*.html
curl -s "$D/" | grep -oE '<script[^>]+src="[^"]+"' | sort -u        # unknown external JS = skimmer/redirector
curl -sI "$D/" | grep -iE 'cf-cache-status|x-cache|x-litespeed-cache|x-proxy-cache|age:'
curl -s "$D/robots.txt"; curl -s "$D/sitemap_index.xml" | head -40; curl -s -o /dev/null -w '%{http_code}\n' "$D/.git/config"
for t in A NS MX TXT; do echo "$t: $(dig +short $t ${D#https://})"; done   # DNS hijack, rogue verification TXT
```

GSC: Security issues · Manual actions · Settings → Users and permissions (unknown owners) · Sitemaps (unknown) · Pages (indexed spike) · URL Inspection → Test live URL (authoritative vs IP-based cloaking). JS sites → chrome-devtools MCP, not curl.

## 12. ⚠ Write commands (approval each, after backup)

```bash
cd "$WEB"; IR=~/ir-$(date +%Y%m%d); ( umask 077; mkdir -p $IR/quarantine )   # outside webroot
# Backup
$WP db export $IR/db-pre.sql                       # needs proc_open; else mysqldump with a 600 defaults file:
( umask 077; c=$IR/.my.cnf; printf '[client]\nuser=%s\npassword=%s\nhost=%s\n' \
  "$(grep -oP "DB_USER['\"]\s*,\s*['\"]\K[^'\"]+" wp-config.php)" \
  "$(grep -oP "DB_PASSWORD['\"]\s*,\s*['\"]\K[^'\"]+" wp-config.php)" \
  "$(grep -oP "DB_HOST['\"]\s*,\s*['\"]\K[^'\":]+" wp-config.php)" > $c )   # never print these
mysqldump --defaults-extra-file=$IR/.my.cnf --single-transaction --no-tablespaces \
  "$(grep -oP "DB_NAME['\"]\s*,\s*['\"]\K[^'\"]+" wp-config.php)" | gzip > $IR/db-pre.sql.gz; rm -f $IR/.my.cnf
tar --exclude='./wp-content/cache' -czf $IR/files-pre.tgz -C "$WEB" .
cp -p wp-config.php $IR/wp-config.php.bak; cp -p .htaccess $IR/htaccess.bak
# Quarantine (keep path in the name, hash first)
f=<path>; sha256sum "$f" >> $IR/quarantine/SHA256SUMS; mv "$f" "$IR/quarantine/$(echo "$f" | tr / _)"
# WP access
$WP user delete <id> --reassign=<legit-admin-id>
for id in $($WP user list --field=ID); do $WP user application-password delete $id --all; $WP user session destroy $id --all; done
$WP user reset-password <ids> --skip-email        # random new pw; owners use Lost Password on their own inbox. Never --show-password
$WP config shuffle-salts                         # supporting step only; some hosts keep salts in a separate file
$WP cron event delete <malicious-hook>
# Clean source
$WP core download --force --skip-content --version=$($WP core version)
$WP plugin install <slug> --force --version=<x>; $WP theme install <parent> --force --version=<x>
# Caches (after cleanup)
n=ocr-$(openssl rand -hex 8).php; printf '<?php opcache_reset(); echo "ok";' > "$WEB/$n"; curl -s "$D/$n"; rm -f "$WEB/$n"   # or: systemctl reload php8.x-fpm
rm -rf /var/cache/nginx/<zone>/* && systemctl reload nginx     # path from: nginx -T | grep proxy_cache_path
$WP db query "DELETE FROM ${P}postmeta WHERE meta_key='_elementor_element_cache'"
$WPFULL litespeed-purge all; $WPFULL cache flush   # plugins loaded on purpose, post-clean
# Cloudflare: dashboard → Caching → Purge Everything
```

## 13. Verify (post-clean)

```bash
for i in $(seq 1 12); do curl -s -o /dev/null "$D/?cb=$RANDOM"; done
$WPFULL cron event run --due-now                   # plugins loaded on purpose: tests regeneration
# then re-run §7 signature + marker greps and §9 stash queries — expect zero new hits. Repeat at 24 h and 7 days.
curl -s -X POST "$D/wp-json/batch/v1" -H 'Content-Type: application/json' -d '{"requests":[]}'   # expect rest_no_route
curl -s "$D/wp-json/wp/v2/users" | head -c 300                                                    # expect no user list
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$D/xmlrpc.php"                                   # expect 403/404/405
curl -s -o /dev/null -w '%{http_code}\n' "$D/.git/config"                                          # expect 403/404
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no <host> true                    # expect publickey denial
ssh -F /dev/null -i <newkey> -o IdentitiesOnly=yes <user>@<ip> true                                # each new key, in isolation
```

Re-run §11 (normal vs bot vs referrer) and finish with GSC URL Inspection live test.
