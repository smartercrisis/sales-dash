# Sales & Returns Dashboard

Built for the "Business Analytics" client request: CSV/Excel upload, city-name
cleanup, revenue metrics, sales charts, return-rate risk alerts, and a
downloadable executive summary.

## Files
- `app.py` — the Streamlit app (UI + charts + alerts + export)
- `core.py` — the data cleaning and city-normalization logic (unit tested separately)
- `requirements.txt` — dependencies

## Fastest free deployment: Streamlit Community Cloud
1. Push these three files to a public (or free-tier private) GitHub repo.
2. Go to share.streamlit.io, sign in with GitHub, click "New app."
3. Point it at the repo and `app.py`. It installs `requirements.txt`
   automatically and gives you a public URL in ~2 minutes.
4. No server management, no sleep/cold-start issues on the free tier for
   light traffic like a single client demo.

## Alternative: Replit
1. Create a new Python Repl, upload the three files.
2. In the Shell tab: `pip install -r requirements.txt`
3. Run: `streamlit run app.py --server.port 8080 --server.address 0.0.0.0`
4. Replit's free tier will sleep the app after inactivity — fine for a
   one-time client review, not for something you want always-on.

## Before you send this to the client
- Ask whether "New Cairo" should count as its own zone or get folded into
  "Cairo" for their reporting — the app currently keeps them separate.
- Confirm their export actually has a returned/not-returned flag per order.
  Without it, the return-rate section will show 0% for everything, which
  will look broken rather than just "no data."
- Test with a real (even partial) export from her before delivery — the
  column-mapping step handles unknown layouts, but real Instagram/manual
  exports often have merged cells or stray header rows that a synthetic
  test file won't catch.
