# Self-hosted API documentation assets

Served by `backend/app/main.py` at `/docs/static/` so `/docs` (Swagger UI) and
`/redoc` (Redoc) work without an internet connection. Byte-identical copies
of published npm packages. Do not edit; regenerate with
`scripts/vendor_api_docs.sh`. The backend serves `redoc.standalone.js` with
one change, made in memory: the CDN address of the logo in Redoc's footer is
emptied (`REDOC_CDN_LOGO` in `backend/app/main.py`).

| Package | Version | License |
|---|---|---|
| [swagger-ui-dist](https://www.npmjs.com/package/swagger-ui-dist) | 5.35.0 | Apache-2.0 (`LICENSE-swagger-ui.txt`, `NOTICE-swagger-ui.txt`; bundled third-party notices in `swagger-ui-bundle.js.LICENSE.txt`) |
| [redoc](https://www.npmjs.com/package/redoc) | 2.5.4 | MIT (`LICENSE-redoc.txt`; bundled third-party notices in `redoc.standalone.js.LICENSE.txt`) |

SHA-256:

```text
3ed612f41e050ca5e7000cad6f1cbe7e7da39f65fca99c02e99e6591056e5837  favicon-32x32.png
dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b  redoc.standalone.js
e6a898692f2d768e807c3ba4626068a69a2c5dd960dd6c76f3e4d3a3de180af2  swagger-ui-bundle.js
5ed08757e53da3e026d6cbecc61fe5d43585c9560b302d534ad56692519a273d  swagger-ui.css
```
