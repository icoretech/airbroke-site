# Airbroke Site

This is the presentation site for the
[Airbroke](https://github.com/icoretech/airbroke) project, an open-source error
catcher.

For detailed information about the Airbroke project, its features, system
requirements, and deployment options, please visit the
[Airbroke GitHub repository](https://github.com/icoretech/airbroke).

If you have any questions or feedback, feel free to
[open an issue](https://github.com/icoretech/airbroke/issues/new) on the Airbroke
repository.

## deployment

The production workflow builds a static export with `NODE_ENV=production` and
publishes it into a private MEGA S4 bucket. Configure these repository-scoped
GitHub Actions values before enabling that workflow:

| kind | name | purpose |
| --- | --- | --- |
| secret | `MEGA_SITE_ACCESS_KEY_ID` | site workload access key |
| secret | `MEGA_SITE_SECRET_ACCESS_KEY` | site workload secret key |
| variable | `MEGA_SITE_BUCKET` | private site bucket |
| variable | `MEGA_SITE_ENDPOINT` | explicit regional S3 API endpoint |
| variable | `MEGA_SITE_REGION` | corresponding signing region |

`scripts/publish-site.py` snapshots the export, rejects symlinks and unsafe
paths, and requires nonempty `index.html` and `404.html`. Releases contain at
most 10,000 files and 512 MiB. A sorted SHA256 manifest determines the immutable
`airbroke/releases/<manifest-sha256>/` prefix. The publisher downloads the whole
release and compares every byte before updating `airbroke/live/`. Support files
are uploaded and read back first; `index.html` is replaced only after they pass
verification. Failed support transfers or an index upload failure preserve the
previous HTML entrypoint. Old hashed assets and archived releases remain
available; this publisher performs no retention deletion. The audit marker
`airbroke/current` is written after the live index.

The public origin uses an authenticated S3 gateway over the stable live prefix;
public object URLs are not required. All gateway replicas see the same objects,
and old hashed assets remain available to cached HTML. `_next/static/` assets
use immutable caching; mutable files use `no-cache`. Publication is serialized.
Repository credentials are separate from organization-wide storage credentials.

This is a single-entrypoint publication contract, not a transaction across the
whole site. Mutable support files such as `index.txt` and `404.html` can change
before the HTML entrypoint. The current presentation site has one page; adding
independently navigable pages requires revisiting that deployment contract.

Run the boundary tests with Python 3.11+, AWS CLI v2 and pytest:

```sh
uv run --with pytest==9.0.2 python -m pytest scripts/tests -q
```

The tests invoke the real publisher and AWS CLI against an isolated HTTP S3
fixture, including corrupt downloads, denied uploads and unsafe exports.
