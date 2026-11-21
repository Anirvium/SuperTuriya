# Run and move SuperTuriya

## Public product website and your own domain

The current public deployment remains available while you purchase your domain.
The website is portable static HTML, CSS, JavaScript and assets in
`sites/superturiya/dist`. It has no build step or server-side runtime dependency.

A ready-to-upload archive is generated with:

```bash
python3 scripts/package_website.py
```

When you know the actual new domain, create a fresh archive with its HTTPS origin:

```bash
python3 scripts/package_website.py --origin https://your-actual-domain.example --output output/website-custom-domain.zip
```

Replace that example origin with your owned domain. The command rewrites
canonical links, social-preview URLs, robots.txt and the sitemap in the archive.
It does not change local source files or publish anything. Extract the ZIP into
the static host's document root; `index.html` must be at that root. Use a host
that resolves `/demo/` and `/docs/` to their nested `index.html` files. Connect
the owned domain through that host's DNS instructions, enable HTTPS, and check
all three routes and the social image before sharing the new link.

The `_headers` file expresses response-security settings for hosts that support
that convention. Other hosts need equivalent configuration. HTML pages also
contain a content-policy meta tag. Neither a domain purchase nor a Git push
automatically switches the currently live URL.

## Local operator

```bash
python3 -m superturiya --seed --port 8765
```

Open http://127.0.0.1:8765 for the repair playground or
http://127.0.0.1:8765/traces.html for your imported traces. SQLite data persists
at `var/superturiya.db` unless `--db` chooses another location. Python 3.9+ is
required; automated validation was run with Python 3.12 on macOS.

## Container definition

The included Dockerfile uses a non-root user and contains only the Python app,
web files and committed benchmark/evidence assets. Compose requires explicit
authentication and scopes, publishes only to host loopback, uses a persistent
data volume, and sets a read-only container filesystem apart from data and tmp.

```bash
export SUPERTURIYA_API_TOKEN='set-a-long-random-secret'
export SUPERTURIYA_API_TENANT='your-tenant'
export SUPERTURIYA_API_PRINCIPAL='your-reviewer'
docker compose up --build -d
docker compose logs -f operator
```

Store secrets through your deployment environment, not in Git. Open the operator
page and enter the token. The container does not seed demo data on startup;
the repair playground can prepare its fixtures on demand.

Docker was unavailable in the development environment for this upgrade. The
definition is supplied for deployment review; an image build, startup, volume
permission and restart smoke test remain required on the target host.

For private remote use, put the operator behind an HTTPS reverse proxy and set
`SUPERTURIYA_ALLOWED_ORIGINS` to the exact HTTPS origin. Do not expose its port
directly as a public anonymous playground. This is one bound operator identity,
not multi-user roles or enterprise single sign-on. Public marketing hosting is
a separate deployment.

## Consistent backups and restore

The backup tool uses SQLite's online backup API so committed WAL data is included.
It verifies database structure and integrity, writes a digest manifest, and
refuses to overwrite an existing backup. Database snapshots contain private
workspace data; protect and retain them accordingly.

```bash
python3 -m superturiya.operations backup --db var/superturiya.db --output output/backups/workspace.db
python3 -m superturiya.operations restore --backup output/backups/workspace.db --manifest output/backups/workspace.db.manifest.json --output var/restored-workspace.db
```

Restore checks the manifest digest and writes to a new database path. Inspect the
restored workspace with `--db var/restored-workspace.db` before choosing it for
normal use. These local backup/restore checks do not establish off-site recovery,
encryption, automated retention, or availability guarantees.
