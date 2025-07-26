# SSH into UniFi Cloud Gateway Ultra (CGU) — Step‑by‑Step Guide

Keep this in your repo for quick reference.

---

## TL;DR

1. **Enable SSH in *****Console Settings → Advanced/Services → SSH*** (not the Network app’s *Device SSH Authentication*).
2. Set a temporary password (UI only supports password at first).
3. From your Mac:
   ```bash
   ssh root@192.168.X.X   # or the username you set
   ```
4. Once in, add your public key so you can stop using the password:
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.X.X
   # OR manually echo the key into /data/ssh/authorized_keys
   ```
5. Reconnect with the key:
   ```bash
   ssh -i ~/.ssh/id_ed25519 root@192.168.X.X
   ```
6. (Optional) Disable/limit password auth and never expose port 22 to the WAN.

---

## Why this dance?

- **Fact:** The CGU UI exposes password-based SSH only.
- **Workaround:** Log in once with a password, then drop your key on the box.
- **Outcome:** Key-based auth = safer, faster, scriptable.

---

## 1. Enable SSH on the Console (not just devices)

1. Open UniFi OS in your browser.
2. Click the **9‑dot launcher** (left sidebar) or the name drop‑down (e.g., *Cloud Gateway Ultra*).
3. Go to **Console Settings** (a.k.a. *System*, *Admin*, or *Advanced*) → **SSH**.
4. Check **I agree to enable SSH** → **Continue**.
5. Set **Username** and **Password**. (You’ll swap to keys shortly.)
6. Save/Apply and wait \~10 seconds for the daemon to start.

> If you only see “Device SSH Authentication,” you’re still in the *Network* app. Back out to the console-level settings.

---

## 2. First Login (password)

From your Mac:

```bash
ssh <username>@192.168.X.X
```

- Accept the host fingerprint: type `yes`.
- Enter the password you set in the UI.

If you get `Connection refused`, SSH isn’t running yet. Toggle the switch off/on and save, or reboot.

If you get `Host key verification failed`, clear the old key and retry:

```bash
ssh-keygen -R 192.168.X.X
```

---

## 3. Add Your SSH Public Key (persistent)

### Option A: Using `ssh-copy-id` from macOS

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <username>@192.168.X.X
```

This appends the key to `~/.ssh/authorized_keys` on the gateway.

### Option B: Manual method on the gateway

```bash
mkdir -p /data/ssh /root/.ssh
cat >> /data/ssh/authorized_keys <<'EOF'
ssh-ed25519 AAAA...your_public_key... comment
EOF
ln -sf /data/ssh/authorized_keys /root/.ssh/authorized_keys
chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
```

`/data` survives upgrades/reboots; symlinking keeps OpenSSH happy.

---

## 4. Reconnect with the Key

```bash
ssh -i ~/.ssh/id_ed25519 <username>@192.168.X.X
```

No password prompt = success.

(Optional) Add a shortcut in `~/.ssh/config`:

```text
Host unifi
  HostName 192.168.X.X
  User <username>
  IdentityFile ~/.ssh/id_ed25519
```

Then run `ssh unifi`.

---

## 5. Harden & Housekeeping

- **Limit exposure:** Don’t forward port 22 to the internet; use VPN/WireGuard if you need remote shell.
- **Long random password:** Even if you rely on keys, set a high-entropy password in case the UI forces it.
- **Disable password auth (if firmware allows):** Look for a toggle or edit `/etc/ssh/sshd_config` (beware upgrades may overwrite).
- **Turn SSH off when you’re done** if you rarely need it.

---

## 6. Common Troubleshooting

| Symptom                        | Fix/Check                                                           |
| ------------------------------ | ------------------------------------------------------------------- |
| `Connection refused`           | SSH daemon not running → toggle SSH, save, or reboot. Confirm IP.   |
| `Host key verification failed` | `ssh-keygen -R 192.168.X.X` to clear old fingerprint.               |
| Password rejected              | Wrong username (try `root`) or typo; confirm in UI.                 |
| Key not accepted after reboot  | Ensure key lives in `/data/ssh/authorized_keys`.                    |
| Stuck in limited shell         | Try `unifi-os shell` (if present) to reach underlying container/OS. |

---

## Appendix: Useful Commands

```bash
# Test if port 22 is open from macOS
nc -vz 192.168.X.X 22

# Restart SSH service (depends on firmware)
/etc/init.d/sshd restart   # or service ssh restart

# Reboot the gateway
reboot

# View running containers (on UniFi OS devices)
podman ps
```

---

## Credits / Disclaimer

- Ubiquiti warns that CLI changes can void warranty; proceed at your own risk.
- Commands confirmed on CGU firmware v4.3.6 (kernel 5.4.213), July 2025.

---

Happy hacking! PRs welcome if UniFi changes the UI/paths.

