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

The [publication workflow](.github/workflows/release.yml) builds the current
source with Node.js 24 and `NODE_ENV=production`, then publishes the Next.js
static export from `out/` to GitHub Pages. Site-related pushes to `main` trigger
publication; the workflow can also be started manually on `main`.

In repository **Settings → Pages**, select **GitHub Actions** as the publishing
source and set the custom domain to `airbroke.icorete.ch`. Configure the domain
in Pages before pointing its DNS record to GitHub Pages, then enable HTTPS.
The public site remains at [airbroke.icorete.ch](https://airbroke.icorete.ch).

The build job has read-only repository access. The deployment job uses the
`github-pages` environment with `pages: write` and `id-token: write`. It deploys
the artifact produced by its own build attempt, after checking that the index
and error pages exist. A newer run supersedes an unfinished older publication.

Publishing uses GitHub's workflow token and OIDC; no S3 credentials, storage
bucket or cluster gateway is required. Keep the site compatible with static
export: server-only Next.js features require a separate hosting decision.
