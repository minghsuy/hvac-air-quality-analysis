# Cleaning Git History - Removing Sensitive Information

## ⚠️ CRITICAL: This Will Rewrite History!

This process will:
1. Change all commit hashes
2. Require force-pushing
3. Break any existing clones/forks
4. Require all collaborators to re-clone

## Step 1: Install BFG Repo-Cleaner

```bash
# On macOS with Homebrew
brew install bfg

# Or download JAR directly
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
```

## Step 2: Create a Backup

```bash
# Clone a fresh copy as backup
cd ~/Documents/Github/
git clone https://github.com/minghsuy/hvac-air-quality-analysis.git hvac-backup
cd hvac-backup
git fetch --all
```

## Step 3: Clean the Repository

```bash
# Go back to main repo
cd ~/Documents/Github/hvac-air-quality-analysis

# Run BFG to replace sensitive strings
bfg --replace-text replacements.txt .

# Or if using JAR:
java -jar bfg-1.14.0.jar --replace-text replacements.txt .
```

## Step 4: Clean Git History

```bash
# BFG will have marked commits for cleaning, now actually clean them
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

## Step 5: Verify the Cleaning

```bash
# Check if sensitive data is gone
git log --all --full-history --oneline --grep="192.168.20"
git log --all --full-history --oneline --grep="d83bda"
git log --all --full-history --oneline --grep="XXXXXXXXXX"

# Check file contents in history
git log -p | grep -E "(192\.168\.20|d83bda|XXXXXXXXXX)"
```

## Step 6: Force Push to GitHub

```bash
# ⚠️ DANGER: This rewrites history on GitHub
git push --force --all
git push --force --tags
```

## Step 7: Clean Up Local References

```bash
# Remove the backup files BFG created
rm -rf .git/refs/original/
rm replacements.txt
rm sensitive-strings.txt
```

## Step 8: Notify Any Collaborators

Anyone who has cloned your repo needs to:

```bash
# Delete their local copy
rm -rf hvac-air-quality-analysis

# Clone fresh
git clone https://github.com/minghsuy/hvac-air-quality-analysis.git
```

## Alternative: Nuclear Option - New Repository

If cleaning seems too risky, you can:

1. Create a new repository
2. Copy only the current clean files
3. Start fresh with no history
4. Archive the old repo as private

```bash
# Create new repo on GitHub first, then:
cd ~/Documents/Github/
mkdir hvac-air-quality-clean
cd hvac-air-quality-clean
git init

# Copy clean files (not .git!)
cp -r ../hvac-air-quality-analysis/* .
cp ../hvac-air-quality-analysis/.gitignore .
cp ../hvac-air-quality-analysis/.env.example .

# Ensure no sensitive data
grep -r "192.168.20" .
grep -r "d83bda" .
grep -r "XXXXXXXXXX" .

# Create initial commit
git add -A
git commit -m "Initial commit - clean history"
git remote add origin https://github.com/minghsuy/hvac-air-quality-clean.git
git push -u origin main
```

## Verification Commands

After cleaning, run these to ensure no sensitive data remains:

```bash
# Search for IPs
git grep -i "192.168.20" $(git rev-list --all)
git grep -i "192.168.X.X" $(git rev-list --all)

# Search for MACs
git grep -i "d83bda" $(git rev-list --all)
git grep -i "d8:3b:da" $(git rev-list --all)

# Search for serial
git grep -i "XXXXXXXXXX" $(git rev-list --all)
```

If any results appear, the cleaning didn't work completely.