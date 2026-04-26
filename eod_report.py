name: EOD NSE Report
on:
  schedule:
    - cron: '0 15 * * 1-5'
  workflow_dispatch:

jobs:
  eod:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install yfinance pandas numpy pytz requests
      - uses: actions/download-artifact@v4
        with:
          name: eod-history
          path: .
        continue-on-error: true
      - run: test -f eod_history.json || echo '{}' > eod_history.json
      - run: python eod_report.py
        env:
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_PASS: ${{ secrets.GMAIL_PASS }}
          TO_EMAIL: ${{ secrets.TO_EMAIL }}
      - uses: actions/upload-artifact@v4
        with:
          name: eod-history
          path: eod_history.json
          retention-days: 90
