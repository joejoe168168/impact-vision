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

**Alternative:** Use `python -m impact_vision` instead (works without PATH changes):

```bash
python -m impact_vision --help
python -m impact_vision catalog stats
python -m impact_vision dd list
```
