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

## Scanned PDFs (pages without a text layer)

Impact Vision reads the PDF text layer. Pages without one, such as scans or
slides exported as pictures, are read by OCR when an OCR backend is available.
Otherwise the log says which pages look scanned.

- **Tesseract:** install it (`apt install tesseract-ocr`, `brew install tesseract`). It is picked up automatically. Set `IMPACT_VISION_OCR_LANG=eng+chi_tra` for more languages.
- **A local OCR or layout model** (GLM-OCR, LightOnOCR-class and similar): point Impact Vision at its command line. Each page is rendered to a PNG, and stdout becomes the page text:

  ```bash
  export IMPACT_VISION_OCR_COMMAND="my-ocr --image {image}"
  ```

- `IMPACT_VISION_DOC_PARSER=auto` (default) OCRs only pages without text. `text` never OCRs, and `ocr` OCRs every page.

All of these options run on your machine, so the document is not sent anywhere.
