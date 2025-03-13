# BBFC Image Fix for Linux Servers

This directory contains scripts to fix issues with BBFC certification images on Linux servers. The problem occurs because Linux file systems are case-sensitive, while Windows file systems are not.

## The Issue

The templates reference BBFC image files with uppercase names (e.g., `img/BBFC_U_(2019).svg`), but on Linux servers, the exact case must match. This causes the images to not be found on Linux servers.

## Solution

The solution is to create lowercase versions of all BBFC image files. This way, both the uppercase and lowercase versions will be available, ensuring compatibility across different operating systems.

## How to Fix

You have two options to fix this issue:

### Option 1: Python Script (Recommended)

1. Upload the `fix_bbfc_linux.py` script to your server
2. Make it executable: `chmod +x fix_bbfc_linux.py`
3. Run the script: `./fix_bbfc_linux.py`
4. Run collectstatic: `python manage.py collectstatic --noinput`

### Option 2: Shell Script

1. Upload the `fix_bbfc_linux.sh` script to your server
2. Make it executable: `chmod +x fix_bbfc_linux.sh`
3. Run the script: `./fix_bbfc_linux.sh`
4. Run collectstatic: `python manage.py collectstatic --noinput`

### Option 3: Manual Fix

If the scripts don't work, you can manually create lowercase versions of the files:

```bash
cd static/img
for file in BBFC_*.svg; do
    cp "$file" "$(echo $file | tr '[:upper:]' '[:lower:]')"
done

# If you have a staticfiles directory
cd ../../staticfiles/img
for file in BBFC_*.svg; do
    cp "$file" "$(echo $file | tr '[:upper:]' '[:lower:]')"
done

# Run collectstatic
python manage.py collectstatic --noinput
```

## Verification

After running one of the fixes, verify that both uppercase and lowercase versions of the BBFC image files exist in your static directories:

```bash
ls -la static/img/BBFC_*.svg static/img/bbfc_*.svg
```

## Long-term Solution

For a more permanent solution, consider updating your templates to use lowercase filenames consistently. This would involve changing references from `img/BBFC_U_(2019).svg` to `img/bbfc_u_(2019).svg` in all your templates. 