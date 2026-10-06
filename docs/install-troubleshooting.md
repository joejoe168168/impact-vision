# Install troubleshooting

**`'impact-vision' is not recognized`?** Run the auto-fix script:

```bash
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\add-to-path.ps1

# Windows CMD
scripts\add-to-path.bat

# Mac/Linux
bash scripts/add-to-path.sh
```

**Important:** After running the script, you must **close and reopen your terminal** (CMD/PowerShell/Terminal) for the PATH change to take effect. Then try `impact-vision --help`.

**Alternative:** Use `python -m openharness` instead (works without PATH changes):

```bash
python -m openharness --help
python -m openharness catalog stats
python -m openharness dd list
```
