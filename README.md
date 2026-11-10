# dead-block

This is a Test of Dead domain include in NeoDevhost
Homepage: https://github.com/neodevpro/neodevhost

## How it works

Every run re-checks the whole accumulated list and replaces `deadblock`, so
domains that came back to life drop out while dead names that upstream removed
from its block list are kept:

1. download <https://raw.githubusercontent.com/neodevpro/neodevhost/master/block>
2. add the names already recorded in `deadblock`
3. resolve every domain concurrently (DNS over HTTPS, plain HTTP fallback, then UDP)
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

Lookups run through DNS over HTTPS (Cloudflare, Google and AliDNS) so local DNS
filters, hosts-file blockers and firewalls that drop UDP/53 cannot skew the
result. If TLS is blocked, the same JSON API is retried over plain HTTP
(AliDNS), and public UDP resolvers are the last resort.

Plain HTTP is unencrypted, so it is only used when no HTTPS endpoint answers.

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
| `--transport` | `CHECK_TRANSPORT` | `auto` | `auto`, `https`, `http` (plain) or `udp` |
| `--endpoints` | `CHECK_ENDPOINTS` | built-in | comma separated DoH URLs, `http://` or `https://` |
| `--resolvers` | `CHECK_RESOLVERS` | `auto` | UDP only: `auto`, `system` or `a,b,c` (`host` or `host:port`) |
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
python check.py --transport http       # DNS over plain HTTP only
python check.py --transport udp        # fall back to plain DNS
python check.py --endpoints https://dns.google/resolve
```

## Using a local resolver (AdGuard Home, dnsmasq, Unbound)

A local forwarder such as AdGuard Home can be used with `--transport udp`:

```bash
python check.py --transport udp --resolvers 127.0.0.1:15353
```

Three settings decide whether it helps or quietly corrupts the result:

1. **Disable all filters.** The AdGuard Home wizard enables *AdGuard DNS filter*
   and *AdAway Default Blocklist*; blocked names then answer `NXDOMAIN` or
   `0.0.0.0` and look dead. That is indistinguishable from a real dead domain
   for names on the blocklists (ads, trackers, telemetry hosts).
2. **Raise the rate limit.** `ratelimit: 20` (queries per second per client) is
   the default; all lookups come from one address, so 2000 domains took 116 s
   with 1830 unknown instead of ~10 s.
3. **Do not add plaintext UDP upstreams to `parallel` mode.** Where the network
   intercepts UDP/53, the injected `0.0.0.0` answer wins the race: with
   `223.5.5.5` added as an upstream, 1630 of 2000 domains were reported as
   sinkholed. Use `https://cloudflare-dns.com/dns-query` and
   `https://dns.google/dns-query` only.

With those three fixed, measured on the same 3000-domain sample:

| concurrency | direct DoH | local AdGuard Home |
|-------------|-----------|--------------------|
| 400 | 16.0 s, 188 unknown | 10.6 s, 49 unknown |
| 800 | 20.9 s, 172 unknown | 13.8 s, 49 unknown |
| 1600 | 26.7 s, 1284 unknown | 11.1 s, 49 unknown |

The gain comes from AdGuard Home querying two upstreams in parallel and reusing
persistent connections, so tail latency and timeouts shrink. It is not needed on
GitHub Actions, where the runner already reaches the public resolvers quickly
(2.2% unknown, near the floor of domains that simply cannot be resolved).
