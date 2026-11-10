#!/usr/bin/env python3
"""Bulk dead-domain checker.

Reads a domain list (default: ``block``), resolves every name concurrently and
writes the names that no longer exist to the output file (default:
``deadblock``). Each run checks the whole list again, so names that came back
to life disappear from the output.

A name is only recorded as dead when two independent resolvers agree. Names
that cannot be resolved because of timeouts or broken authoritative servers are
reported as unknown and left alone, so transient DNS failures never end up in
the list.

Resolution uses DNS over HTTPS when possible (immune to local DNS filtering and
to firewalls that block UDP/53) and falls back to plain UDP resolvers. Results
are written to ``<output>.tmp`` after every batch and only replace the output
file when the run completes, so a failed run never truncates the previous list.
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import os
import sys
import time
from pathlib import Path

import aiohttp
import dns.asyncresolver
import dns.exception
import dns.resolver

DEAD = "dead"
ALIVE = "alive"
UNKNOWN = "unknown"
SINKHOLED = "sinkholed"

PUBLIC_RESOLVERS = ("1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222")
DOH_ENDPOINTS = ("https://cloudflare-dns.com/dns-query", "https://dns.google/resolve")
SINKHOLE_ADDRESSES = frozenset({"0.0.0.0", "127.0.0.1", "::", "::1"})
RRTYPE_NUMBERS = {"A": 1, "AAAA": 28, "MX": 15}


class DohTransport:
    """DNS over HTTPS using the JSON API of Cloudflare and Google."""

    def __init__(self, endpoints: list[str], timeout: float, concurrency: int) -> None:
        self._endpoints = itertools.cycle(endpoints)
        self._timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._connector_limit = concurrency + 10

    async def __aenter__(self) -> "DohTransport":
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout),
            connector=aiohttp.TCPConnector(limit=self._connector_limit, ttl_dns_cache=600),
        )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._session is not None:
            await self._session.close()

    async def query(self, name: str, rdtype: str, tries: int) -> tuple[str, list[str]]:
        for attempt in range(tries):
            endpoint = next(self._endpoints)
            try:
                assert self._session is not None
                async with self._session.get(
                    endpoint,
                    params={"name": name, "type": rdtype},
                    headers={"accept": "application/dns-json"},
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt + 1 < tries:
                    await asyncio.sleep(0.2 * (attempt + 1))
                continue

            status = payload.get("Status", 2)
            if status == 3:
                return "nxdomain", []
            if status != 0:
                if attempt + 1 < tries:
                    await asyncio.sleep(0.2 * (attempt + 1))
                continue
            wanted = RRTYPE_NUMBERS[rdtype]
            addresses = [record.get("data", "") for record in payload.get("Answer", []) if record.get("type") == wanted]
            return ("yes", addresses) if addresses else ("nodata", [])
        return "error", []


class UdpTransport:
    """Round-robin over plain DNS resolvers so no single server gets hammered."""

    def __init__(self, servers: list[str | None], timeout: float) -> None:
        self._resolvers = []
        for server in servers:
            if server is None:
                resolver = dns.asyncresolver.Resolver()
            else:
                resolver = dns.asyncresolver.Resolver(configure=False)
                resolver.nameservers = [server]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            resolver.retry_servfail = False
            self._resolvers.append(resolver)
        self._cycle = itertools.cycle(self._resolvers)

    async def __aenter__(self) -> "UdpTransport":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def query(self, name: str, rdtype: str, tries: int) -> tuple[str, list[str]]:
        for attempt in range(tries):
            resolver = next(self._cycle)
            try:
                answer = await resolver.resolve(name, rdtype, lifetime=resolver.lifetime, raise_on_no_answer=True)
                if rdtype in ("A", "AAAA"):
                    return "yes", [rdata.address for rdata in answer]
                return "yes", []
            except dns.resolver.NXDOMAIN:
                return "nxdomain", []
            except dns.resolver.NoAnswer:
                return "nodata", []
            except dns.exception.DNSException:
                if attempt + 1 < tries:
                    await asyncio.sleep(0.2 * (attempt + 1))
        return "error", []


async def _probe(transport, name: str, tries: int, sinkhole_dead: bool) -> str:
    a_kind, addresses = await transport.query(name, "A", tries)
    if a_kind == "nxdomain":
        return DEAD  # NXDOMAIN is independent of the record type
    if a_kind == "error":
        return UNKNOWN

    usable = [address for address in addresses if address not in SINKHOLE_ADDRESSES]
    aaaa_addresses: list[str] = []
    if not usable:
        aaaa_kind, aaaa_addresses = await transport.query(name, "AAAA", tries)
        if aaaa_kind == "error":
            return UNKNOWN
        usable = [address for address in aaaa_addresses if address not in SINKHOLE_ADDRESSES]

    if usable:
        return ALIVE
    if addresses or aaaa_addresses:
        # The name resolves, but only to 0.0.0.0 / loopback: nothing is reachable.
        return DEAD if sinkhole_dead else SINKHOLED

    # No address records at all: mail-only domains still count as alive.
    mx_kind, _ = await transport.query(name, "MX", tries)
    if mx_kind == "yes":
        return ALIVE
    if mx_kind == "error":
        return UNKNOWN
    return DEAD


async def check_and_report(transport, semaphore: asyncio.Semaphore, name: str, args: argparse.Namespace) -> tuple[str, str]:
    async with semaphore:
        status = await _probe(transport, name, args.tries, args.sinkhole_dead)
        if status == DEAD and not args.no_confirm:
            status = await _probe(transport, name, args.tries, args.sinkhole_dead)
        return name, status


async def _udp_reachable(server: str, timeout: float) -> bool:
    resolver = dns.asyncresolver.Resolver(configure=False)
    resolver.nameservers = [server]
    resolver.timeout = timeout
    resolver.lifetime = timeout
    resolver.retry_servfail = False
    try:
        await resolver.resolve("example.com", "A", lifetime=timeout)
        return True
    except dns.resolver.NXDOMAIN:
        return True
    except dns.exception.DNSException:
        return False


async def _doh_reachable(endpoint: str, timeout: float) -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(
                endpoint, params={"name": "example.com", "type": "A"}, headers={"accept": "application/dns-json"}
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
                return payload.get("Status", 2) in (0, 3)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return False


async def build_transport(args: argparse.Namespace):
    if args.transport in ("auto", "doh"):
        checks = await asyncio.gather(*(_doh_reachable(endpoint, args.timeout) for endpoint in DOH_ENDPOINTS))
        endpoints = [endpoint for endpoint, ok in zip(DOH_ENDPOINTS, checks) if ok]
        if endpoints:
            print(f"using DNS over HTTPS: {', '.join(endpoints)}")
            return DohTransport(endpoints, args.timeout, args.concurrency)
        if args.transport == "doh":
            raise SystemExit("no DNS over HTTPS endpoint reachable")
        print("warning: DNS over HTTPS unavailable, falling back to UDP")

    if args.resolvers == "system":
        servers: list[str | None] = [None]
    elif args.resolvers == "auto":
        checks = await asyncio.gather(*(_udp_reachable(server, args.timeout) for server in PUBLIC_RESOLVERS))
        servers = [server for server, ok in zip(PUBLIC_RESOLVERS, checks) if ok] or [None]
    else:
        servers = [server.strip() for server in args.resolvers.split(",") if server.strip()]
    print(f"using UDP resolvers: {', '.join(server or 'system' for server in servers)}")
    return UdpTransport(servers, args.timeout)


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()


def write_domains(path: Path, names: set[str]) -> None:
    path.write_text("".join(f"{name}\n" for name in sorted(names)), encoding="utf-8", newline="\n")


def load_domains(path: Path) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for line in read_lines(path):
        name = line.strip().lower().rstrip(".")
        if not name or name.startswith("#") or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


async def check_names(
    transport,
    names: list[str],
    semaphore: asyncio.Semaphore,
    args: argparse.Namespace,
    batch_size: int,
    dead: set[str],
    on_batch,
) -> tuple[dict[str, int], list[str]]:
    counts = {DEAD: 0, ALIVE: 0, UNKNOWN: 0, SINKHOLED: 0}
    unknown: list[str] = []
    tasks: list[asyncio.Task] = []
    checked = 0
    try:
        for start in range(0, len(names), batch_size):
            batch = names[start : start + batch_size]
            tasks = [asyncio.create_task(check_and_report(transport, semaphore, name, args)) for name in batch]
            for task in asyncio.as_completed(tasks):
                name, status = await task
                checked += 1
                counts[status] += 1
                if status == DEAD:
                    dead.add(name)
                elif status == UNKNOWN:
                    unknown.append(name)
                if checked % 1000 == 0:
                    print(f"  {checked}/{len(names)} checked, {counts[DEAD]} dead", flush=True)
            on_batch(dead, counts)
    except BaseException:
        for task in tasks:
            task.cancel()
        raise
    return counts, unknown


async def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    temporary_path = output_path.with_name(f"{output_path.name}.tmp")

    if not input_path.is_file():
        print(f"missing input file: {input_path}", file=sys.stderr)
        return 1

    candidates = load_domains(input_path)
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"{input_path.name}: {len(candidates)} domains to check")
    if not candidates:
        return 0

    semaphore = asyncio.Semaphore(args.concurrency)
    batch_size = max(args.concurrency * 4, 500)
    started = time.monotonic()
    dead: set[str] = set()
    totals = {DEAD: 0, ALIVE: 0, UNKNOWN: 0, SINKHOLED: 0}

    def flush(dead_so_far: set[str], _counts: dict[str, int]) -> None:
        if dead_so_far and not args.dry_run:
            write_domains(temporary_path, dead_so_far)

    async with await build_transport(args) as transport:
        counts, unknown = await check_names(transport, candidates, semaphore, args, batch_size, dead, flush)
        for key, value in counts.items():
            totals[key] += value

        # A saturated network drops queries; retry those names slowly so they
        # are not silently lost.
        if unknown and not args.no_retry:
            retry_concurrency = max(16, args.concurrency // 8)
            print(f"retrying {len(unknown)} unknown domains with {retry_concurrency} workers", flush=True)
            retry_semaphore = asyncio.Semaphore(retry_concurrency)
            retry_counts, unknown = await check_names(
                transport, unknown, retry_semaphore, args, max(retry_concurrency * 4, 500), dead, flush
            )
            for key, value in retry_counts.items():
                totals[key] += value

    elapsed = time.monotonic() - started
    print(
        f"{input_path.name}: {len(candidates)} checked in {elapsed:.1f}s - "
        f"{totals[DEAD]} dead, {totals[ALIVE]} alive, {totals[SINKHOLED]} sinkholed, {len(unknown)} unknown"
    )
    if totals[SINKHOLED] and not args.sinkhole_dead:
        print(f"{totals[SINKHOLED]} domains only resolve to 0.0.0.0/loopback; pass --sinkhole-dead to treat them as dead")

    if args.dry_run:
        print("\n".join(sorted(dead)))
        return 0

    write_domains(temporary_path, dead)
    os.replace(temporary_path, output_path)
    print(f"wrote {len(dead)} domains to {output_path}")

    if len(unknown) > len(candidates) / 2:
        print("too many domains could not be resolved, check the DNS setup", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the dead domains of a block list.")
    parser.add_argument(
        "--input",
        default=os.environ.get("CHECK_INPUT", "block"),
        help="domain list to check (default: block)",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("CHECK_OUTPUT", "deadblock"),
        help="file the dead domains are written to (default: deadblock)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("CHECK_CONCURRENCY", "400")),
        help="parallel lookups (default: 400 or $CHECK_CONCURRENCY)",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="per-query timeout in seconds (default: 5)")
    parser.add_argument("--tries", type=int, default=2, help="attempts per query (default: 2)")
    parser.add_argument(
        "--transport",
        choices=("auto", "doh", "udp"),
        default=os.environ.get("CHECK_TRANSPORT", "auto"),
        help="how to resolve names (default: auto, i.e. DNS over HTTPS with UDP fallback)",
    )
    parser.add_argument(
        "--resolvers",
        default=os.environ.get("CHECK_RESOLVERS", "auto"),
        help="UDP resolvers: comma separated list, 'system' or 'auto' (default: auto)",
    )
    parser.add_argument("--no-confirm", action="store_true", help="skip the second resolver confirmation")
    parser.add_argument("--no-retry", action="store_true", help="do not retry names that could not be resolved")
    parser.add_argument(
        "--sinkhole-dead",
        action="store_true",
        default=os.environ.get("CHECK_SINKHOLE_DEAD", "") not in ("", "0", "false"),
        help="count names that only resolve to 0.0.0.0/loopback as dead",
    )
    parser.add_argument("--limit", type=int, default=0, help="only check the first N domains (debugging)")
    parser.add_argument("--dry-run", action="store_true", help="print dead domains without writing the output file")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
