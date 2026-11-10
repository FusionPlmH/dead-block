# dead-block

This is a Test of Dead domain include in NeoDevhost
Homepage: https://github.com/neodevpro/neodevhost

## How it works

Every run re-checks the whole accumulated list and replaces `deadblock`, so
domains that came back to life drop out while dead names that upstream removed
from its block list are kept:

1. download <https://raw.githubusercontent.com/neodevpro/neodevhost/master/block>
2. add the names already recorded in `deadblock`
3. resolve every domain concurrently (DNS over HTTPS, UDP fallback)
4. collect the dead domains in `deadblock.tmp` and swap it into `deadblock` when
   the run finishes

The ~114k-domain list is checked in a few minutes (`CHECK_CONCURRENCY`, 2000 in
the workflow). Because the swap only happens at the end, a failed run leaves the
previous `deadblock` untouched; the partial result stays in the ignored
`deadblock.tmp`. Names that could not be resolved are retried once with a much
smaller worker pool, so pushing the concurrency up does not silently lose
domains when the network starts dropping queries.

## Files

| Path | Purpose |
|------|---------|
| `check.py` | Bulk dead-domain checker (async DNS over HTTPS, UDP fallback) |
| `deadblock` | The result: dead domains, sorted and de-duplicated |
| `deadblock.tmp` | Transient progress file (ignored by git) |
| `.github/workflows/check.yml` | Download, check and commit `deadblock` |

## How a domain is classified

| Result | Meaning |
|--------|---------|
| dead | NXDOMAIN, or the name exists but has no A/AAAA/MX record |
| alive | at least one A/AAAA address other than `0.0.0.0`/loopback, or an MX record |
| sinkholed | only `0.0.0.0`/loopback answers (counted separately, added only with `--sinkhole-dead`) |
| unknown | timeouts or SERVFAIL on every resolver (never written to `deadblock`) |

Lookups run through DNS over HTTPS (Cloudflare and Google) so local DNS filters,
hosts-file blockers and firewalls that drop UDP/53 cannot skew the result. If no
DoH endpoint answers, the checker falls back to public UDP resolvers.

A name is only recorded as dead after a second independent resolver confirms it,
so transient DNS failures never end up in `deadblock`.

## Options

| Option | Environment | Default | Purpose |
|--------|-------------|---------|---------|
| `--input` | `CHECK_INPUT` | `block` | domain list to check |
| `--output` | `CHECK_OUTPUT` | `deadblock` | file the dead domains are written to |
| `--concurrency` | `CHECK_CONCURRENCY` | 400 | parallel lookups |
| `--timeout` | | 5 | seconds per query |
| `--tries` | | 2 | attempts per query |
| `--transport` | `CHECK_TRANSPORT` | `auto` | `auto`, `doh` or `udp` |
| `--resolvers` | `CHECK_RESOLVERS` | `auto` | UDP only: `auto`, `system` or `a,b,c` |
| `--sinkhole-dead` | `CHECK_SINKHOLE_DEAD` | off | treat `0.0.0.0`/loopback-only names as dead |
| `--no-confirm` | | off | skip the second-resolver confirmation |
| `--no-retry` | | off | do not retry names that could not be resolved |
| `--limit` | | 0 | only check the first N domains (debugging) |
| `--fresh` | | off | ignore the existing `deadblock` and rebuild it from the input only |
| `--dry-run` | | off | print dead domains without writing `deadblock` |

## Local run

```bash
pip install dnspython aiohttp
curl -fsSL -o block https://raw.githubusercontent.com/neodevpro/neodevhost/master/block

python check.py                 # block -> deadblock
python check.py --limit 500 --dry-run
python check.py --transport udp # fall back to plain DNS
```
