# photo.tstowx.com

Standalone Hugo portfolio using the photography bundles in `content/photos`.

Local preview from the repository root:

```sh
hugo server --source portfolio --destination /tmp/tstowx-photo-preview --port 1314
```

The site is intended to be deployed as a second Netlify site with `portfolio/` as its base directory. Netlify will then use `portfolio/netlify.toml` automatically. DNS has not been changed.
