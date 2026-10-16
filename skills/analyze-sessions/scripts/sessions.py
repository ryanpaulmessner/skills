#!/usr/bin/env python3
"""Extract, search and count human messages from Claude Code, Pi and Codex transcripts.

Python 3 standard library only. Output is redacted. Writes only to
~/.cache/analyze-sessions/ (folder 700, files 600) unless --out is given.
extract merges into the cache, so rows from deleted transcripts are kept.
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(HOME, ".cache", "analyze-sessions")
DEFAULT_DB = os.path.join(CACHE_DIR, "messages.jsonl")

CLAUDE_GLOB = os.path.join(HOME, ".claude", "projects", "*", "*.jsonl")  # top level only: skips subagents/
PI_GLOB = os.path.join(HOME, ".pi", "agent", "sessions", "*", "*.jsonl")
CLAUDE_HISTORY = os.path.join(HOME, ".claude", "history.jsonl")  # prompt log; fallback for deleted transcripts
CODEX_HISTORY = os.path.join(HOME, ".codex", "history.jsonl")  # never read ~/.codex/auth.json

# ---------------------------------------------------------------- redaction

_REDACT = [
    # Asana PAT: 2/1234567890/1234567890:0123456789abcdef0123456789abcdef
    (re.compile(r"\b\d/\d{6,}/\d{6,}:[0-9a-fA-F]{32}\b"), "[REDACTED-ASANA]"),
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{16,}"), "sk-[REDACTED]"),
    (re.compile(r"\b((?:sk|rk|pk)_(?:live|test)_)[0-9A-Za-z]{10,}"), r"\1[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "AIza[REDACTED]"),
    (re.compile(r"\b(gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"), r"\1[REDACTED]"),
    (re.compile(r"\b(xox[abprse]-)[A-Za-z0-9\-]{10,}"), r"\1[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[REDACTED-JWT]"),
    # Authorization headers (Basic / Bearer / Token / bare value)
    (re.compile(r"(?i)\b(authorization[\"']?\s*[:=]\s*[\"']?(?:basic|bearer|token|digest)?\s*)[^\s\"',;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b((?:bearer|basic)\s+)[A-Za-z0-9._\-~+/]{12,}=*"), r"\1[REDACTED]"),
    # URL-encoded Asana PAT (OAuth callbacks): 2%2F…%2F…%3A<32 hex>
    (re.compile(r"\b\d%2F\d{6,}%2F\d{6,}%3A[0-9a-fA-F]{32}\b", re.I), "[REDACTED-ASANA]"),
    # secret query parameters: ?code=…&access_token=…
    (re.compile(r"(?i)([?&#](?:code|access_token|refresh_token|id_token|client_secret|api_key|apikey|key|token|secret|password|sig|signature)=)[^&#\s\"']+"),
     r"\1[REDACTED]"),
    # user:password@ in URLs
    (re.compile(r"(\w+://[^\s:/@]+:)[^\s@/]{3,}(@)"), r"\1[REDACTED]\2"),
    # password/passwd/pwd/secret/token/api_key = value or : value, any length
    (re.compile(
        r"(?i)\b(\w*(?:password|passwd|pwd|secret|token|api[_-]?key))([\"']?\s*[:=]\s*[\"']?)([^\s\"',;]+)"
    ), r"\1\2[REDACTED]"),
    # other *key = value (8+ chars, so "monkey: x" is kept)
    (re.compile(r"(?i)\b(\w*key)([\"']?\s*[:=]\s*[\"']?)([^\s\"',;]{8,})"), r"\1\2[REDACTED]"),
    # key/token/secret/password <space> value: only values that look random (20+ chars with a digit)
    (re.compile(
        r"(?i)\b(key|token|secret|password)(\s+(?:is\s+)?)(?=\S*\d)([A-Za-z0-9+/_\-.=]{20,})"
    ), r"\1\2[REDACTED]"),
    # bare long hex runs (likely keys) anywhere
    (re.compile(r"\b[0-9a-fA-F]{40,}\b"), "[REDACTED-HEX]"),
    # bare long base64 runs; paths are kept (see _b64)
    (re.compile(r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]*[0-9])(?=[A-Za-z0-9+/]*[A-Z])[A-Za-z0-9+/]{48,}={0,2}"), "_b64"),
]

# A path segment is a word, CamelCase or snake-free name: lib, MyAppWeb, Overview2Kpi, KPI, v19.
_PATH_SEG = re.compile(r"^(?:[A-Z]{1,4}[a-z0-9]*|[a-z0-9]+)+$")


def _b64(m):
    s = m.group(0)
    segs = [x for x in s.split("/") if x]
    if "/" in s and "+" not in s and not s.endswith("=") and len(segs) >= 2 and all(_PATH_SEG.match(x) for x in segs):
        return s  # looks like a file path: keep it greppable
    return "[REDACTED-B64]"


def redact(text):
    for rx, rep in _REDACT:
        text = rx.sub(_b64 if rep == "_b64" else rep, text)
    return text


# ---------------------------------------------------------------- helpers

def iso(ts):
    """Return an ISO UTC string (YYYY-MM-DDTHH:MM:SSZ) from ISO text or epoch seconds/ms."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            ts = ts / 1000.0
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    else:
        d = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        d = d.astimezone(dt.timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def row_key(tool, session, ts, text):
    """Merge key: (tool, session, ts, hash of the raw text). Raw, so a redaction change does not duplicate rows."""
    h = hashlib.sha1(f"{tool}\x1f{session}\x1f{ts}\x1f{text}".encode("utf-8", "replace")).hexdigest()
    return h[:20]


def row(tool, session, cwd, ts, text, source="human"):
    raw = text.strip()
    ts = iso(ts)
    text = redact(raw)
    return {"tool": tool, "session": session, "cwd": cwd, "ts": ts, "text": text, "len": len(text),
            "source": source, "key": row_key(tool, session, ts, raw)}


def secure_write_open(path):
    """Open path for writing with mode 600; create the parent folder if needed."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(path, 0o600)
    return os.fdopen(fd, "w", encoding="utf-8")


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)


def one_line(s, width=200):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= width else s[: width - 1] + "…"


# ---------------------------------------------------------------- extractors

_CC_SKIP_PREFIX = ("<local-command", "<bash-input", "<bash-stdout", "<bash-stderr", "<task-notification",
                   "<system-reminder", "[Request interrupted", "<local-command-caveat", "Another Claude session")
_SYSREM = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
_CMD_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.S)
_CMD_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)


def extract_claude(since):
    for path in glob.glob(CLAUDE_GLOB):
        if since and os.path.getmtime(path) < since.timestamp():
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"type":"user"' not in line:  # fast prefilter; the files are large
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("type") != "user" or e.get("isMeta") or e.get("isCompactSummary") or e.get("isSidechain"):
                    continue
                origin = (e.get("origin") or {}).get("kind")
                if origin and origin != "human":  # task-notification, peer (other agents)
                    continue
                if e.get("promptSource") == "sdk":
                    continue
                c = e.get("message", {}).get("content")
                if isinstance(c, list):
                    if any(b.get("type") == "tool_result" for b in c):
                        continue
                    text = "".join(b.get("text", "") for b in c if b.get("type") == "text")
                else:
                    text = c or ""
                text = _SYSREM.sub("", text).strip()
                if not text:
                    continue
                if "<command-name>" in text:
                    if origin != "human":
                        continue
                    name, args_ = _CMD_NAME.search(text), _CMD_ARGS.search(text)
                    text = (name.group(1).strip() + " " + (args_.group(1).strip() if args_ else "")).strip()
                elif text.startswith(_CC_SKIP_PREFIX):
                    continue
                yield row("claude", e.get("sessionId") or os.path.basename(path)[:-6], e.get("cwd"),
                          e.get("timestamp"), text)


def extract_pi(since):
    for path in glob.glob(PI_GLOB):
        if since and os.path.getmtime(path) < since.timestamp():
            continue
        session, cwd = os.path.basename(path)[:-6], None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                t = e.get("type")
                if t == "session":
                    session, cwd = e.get("id", session), e.get("cwd")
                    continue
                if t != "message" or e.get("message", {}).get("role") != "user":
                    continue
                c = e["message"].get("content")
                text = c if isinstance(c, str) else "".join(
                    b.get("text", "") for b in (c or []) if b.get("type") == "text")
                if not text.strip():
                    continue
                source = "relay" if text.lstrip().startswith("[relay ") else "human"
                yield row("pi", session, cwd, e.get("timestamp"), text, source)


def extract_codex(since):
    if not os.path.exists(CODEX_HISTORY):
        return
    with open(CODEX_HISTORY, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("text", "").strip():
                yield row("codex", e.get("session_id"), None, e.get("ts"), e["text"])


_PASTE_PH = re.compile(r"\[Pasted text #\d+(?: \+\d+ lines)?\]")
_BARE_SLASH = re.compile(r"^/[\w:-]+$")
# prompts that hooks or agent tooling typed into Claude Code, not Ryan (seen in history.jsonl)
_AUTOMATED = re.compile(r"^\[\w+\] bd\.[\w-]+ •|^Check your hook for ")


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def extract_claude_history(since, known):
    """Rows from ~/.claude/history.jsonl that no transcript row already has.

    known: {session: [normalized redacted texts]} from transcripts and the existing cache.
    """
    if not os.path.exists(CLAUDE_HISTORY):
        return
    with open(CLAUDE_HISTORY, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            text, sess = (e.get("display") or "").strip(), e.get("sessionId")
            if not text or _BARE_SLASH.match(text) or text.startswith(_CC_SKIP_PREFIX) or _AUTOMATED.match(text):
                continue  # same filters as transcripts (bare /model, injected markup), plus hook prompts
            seen = known.get(sess)
            if seen:
                # compare the typed part only: history shows pastes as "[Pasted text #1 +69 lines]"
                parts = [_norm(redact(p)) for p in _PASTE_PH.split(text) if _norm(p)]
                if not parts or all(any(p in t for t in seen) for p in parts):
                    continue
            yield row("claude", sess, e.get("project"), e.get("timestamp"), text, "history")


EXTRACTORS = {"claude": extract_claude, "pi": extract_pi, "codex": extract_codex}

# ---------------------------------------------------------------- loading / filtering

def load(args):
    db = getattr(args, "db", None) or DEFAULT_DB
    if not os.path.exists(db):
        sys.exit(f"No data at {db}. Run: sessions.py extract")
    since = args.since
    tool = getattr(args, "tool", "all")
    rows = []
    with open(db, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if tool != "all" and r["tool"] != tool:
                continue
            if since and (r["ts"] or "") < since.strftime("%Y-%m-%dT%H:%M:%SZ"):
                continue
            rows.append(r)
    rows.sort(key=lambda r: (r["ts"] or "", r["tool"], r["session"] or ""))
    return rows


HUMAN = {"human", "history"}  # history = Claude prompt log row with no transcript


def fmt(r, width=200):
    tag = "" if r["source"] == "human" or r["text"].startswith("[relay") else f"[{r['source']}] "
    return f"{r['ts']} {r['tool']:<6} {(r['session'] or '-')[:8]}: {tag}{one_line(redact(r['text']), width)}"


# ---------------------------------------------------------------- commands

def read_rows(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def legacy_key(r):
    # rows written before keys existed: hash of the stored (redacted) text
    return row_key(r["tool"], r["session"], r["ts"], r["text"])


def cmd_extract(args):
    out = args.out or DEFAULT_DB
    if not args.out:
        ensure_cache_dir()
    tools = list(EXTRACTORS) if args.tool == "all" else [args.tool]
    floor = args.since.strftime("%Y-%m-%dT%H:%M:%SZ") if args.since else None

    merged = {}  # key -> row; existing rows are never dropped
    if not args.rebuild:
        for r in read_rows(out):
            r["text"] = redact(r["text"])  # apply the current rules to old rows
            r["len"] = len(r["text"])
            merged[r.get("key") or legacy_key(r)] = r
    before = len(merged)

    added = collections.Counter()

    def add(r):
        if floor and (r["ts"] or "") < floor:
            return
        if r["key"] not in merged:
            merged[r["key"]] = r
            added[(r["tool"], r["source"])] += 1

    for t in tools:
        for r in EXTRACTORS[t](args.since):
            add(r)
    if "claude" in tools:
        known = collections.defaultdict(list)
        for r in merged.values():
            if r["tool"] == "claude":
                known[r["session"]].append(_norm(r["text"]))
        for r in extract_claude_history(args.since, known):
            add(r)

    rows = sorted(merged.values(), key=lambda r: (r["ts"] or "", r["tool"], r["session"] or "", r["key"] if "key" in r else ""))
    tmp = out + ".tmp"
    with secure_write_open(tmp) as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, out)
    os.chmod(out, 0o600)

    for (t, src), n in sorted(added.items()):
        print(f"added {t:<6} {src:<7} {n}")
    total = collections.Counter((r["tool"], r["source"]) for r in rows)
    print("total: " + ", ".join(f"{t}/{src} {n}" for (t, src), n in sorted(total.items())))
    mode = "rebuilt" if args.rebuild else f"merged into {before} existing rows"
    print(f"{mode}: added {sum(added.values())}, now {len(rows)} rows in {out}")


def tail(items, n):
    return items[-n:] if n > 0 else []


def by_session(rows):
    s = collections.defaultdict(list)
    for r in rows:
        s[(r["tool"], r["session"])].append(r)
    return s


def cmd_grep(args):
    try:
        rx = re.compile(args.regex, re.I)
    except re.error as err:
        print(f"error: bad regex {args.regex!r}: {err}", file=sys.stderr)
        sys.exit(2)
    rows = load(args)
    if not args.C:
        for r in rows:
            if rx.search(r["text"]):
                print(fmt(r))
        return
    for key, msgs in by_session(rows).items():
        shown = set()
        for i, r in enumerate(msgs):
            if not rx.search(r["text"]):
                continue
            lo, hi = max(0, i - args.C), min(len(msgs), i + args.C + 1)
            if shown and lo > max(shown) + 1:
                print("--")
            for j in range(lo, hi):
                if j not in shown:
                    print(("> " if j == i else "  ") + fmt(msgs[j]))
                    shown.add(j)
        if shown:
            print("==")


PROMPT_FILE = re.compile(r"tickets/\S*?(?:-prompt\.md|prompts?/\S+\.md)")


def cmd_stats(args):
    rows = load(args)
    human = [r for r in rows if r["source"] in HUMAN]
    n_hist = sum(r["source"] == "history" for r in rows)
    print(f"messages: {len(rows)} (human {len(human)}, of which from claude history.jsonl {n_hist}; relay {len(rows) - len(human)})")
    print("per tool: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(r["tool"] for r in rows).most_common()))
    weeks = collections.Counter()
    for r in rows:
        y, w, _ = parse_ts(r["ts"]).isocalendar()
        weeks[(f"{y}-W{w:02d}", r["tool"])] += 1
    print("per week:")
    for wk in sorted({w for w, _ in weeks}):
        print(f"  {wk}: " + ", ".join(f"{t} {weeks[(wk, t)]}" for t in EXTRACTORS if weeks[(wk, t)]))

    long_ = [r for r in human if r["len"] > 1500]
    print(f"long pastes (>1500 chars): {len(long_)}")
    for r in tail(long_, args.n):
        print("  " + fmt(r, 140))

    dups, short_dups, splits = [], [], []
    last_text = {}
    for key, msgs in by_session(rows).items():
        for a, b in zip(msgs, msgs[1:]):
            if (parse_ts(b["ts"]) - parse_ts(a["ts"])).total_seconds() < 3:
                splits.append(b)
    for r in human:
        t = parse_ts(r["ts"])
        prev = last_text.get(r["text"])
        if prev and (t - prev).total_seconds() <= 3600:
            (short_dups if r["len"] < 20 else dups).append(r)
        last_text[r["text"]] = t
    print(f"exact duplicates within 1 h (20+ chars): {len(dups)}")
    for r in tail(dups, args.n):
        print("  " + fmt(r, 140))
    print(f"short duplicates within 1 h (<20 chars, e.g. 'continue'): {len(short_dups)}")
    for r in tail(short_dups, args.n):
        print("  " + fmt(r, 140))
    print(f"sent <3 s after previous (split pastes): {len(splits)}")
    for r in tail(splits, args.n):
        print("  " + fmt(r, 140))
    pf = [r for r in rows if PROMPT_FILE.search(r["text"])]
    print(f"point at a prompt file: {len(pf)} (relay {sum(r['source'] == 'relay' for r in pf)})")
    for r in tail(pf, args.n):
        print("  " + fmt(r, 140))


# Regex families. Tuned against the history up to 2026-10-05; edit freely.
FAMILIES = {
    "correction": r"that'?s not what i (asked|meant|said)|why (did|would|are|is|were|didn'?t|hasn'?t|isn'?t|wasn'?t) (you|it|this|we|that|there)"
                  r"|wrong (branch|file|repo|worktree|one|place)|\bnope\b|^no[,. ]|\bstill (not|isn'?t|doesn'?t|broken|failing|seeing|showing|getting)"
                  r"|i (said|told you|asked you)|you (missed|forgot|didn'?t)|where did (everything|it|that|the) go|not what i|that'?s wrong"
                  r"|doesn'?t (work|look right|make (any )?sense)|ai slop|try again|\bundo\b|i'?m confused",
    "where_were_we": r"where (were|are) we|forgot where|i forgot|do you remember|remind me|pick (it|this) back up|popping (the|hte) stack"
                     r"|it'?s (the next|now) (monday|tuesday|wednesday|thursday|friday|morning|day)|it'?s (monday|tuesday|wednesday|thursday|friday) the next",
    "retyped_rule": r"co-?author|no trailers?|just me\b|as ryan|formatting churn|format(ting)? only|--no-track|(in|on) a (new )?worktree"
                    r"|precommit|plain language|human[- ]readable|eli5|dumb it down|too dense|\bterse\b|logical commits|granular commits"
                    r"|don'?t push|no push|without much context|w/o (much )?context",
    "relay_paste": r"here'?s the (report|summary|review)|<pasted_content|\blanded\b|reviewer|the (other|build|building|review) session"
                   r"|^\s*(STATUS|REPORT):|\bslice \d+ is complete|nothing is committed|committed as [0-9a-f]{7}|\b\d+ tests(,| passed)"
                   r"|^(fixed|implemented|completed|built|done)\b.{0,40}(\.|:)",
}


TYPED_MAX = 600  # longer messages are pasted prompts or reports, not typed corrections
PASTE = re.compile(r"^\s*<pasted_content", re.I)


def is_typed(r):
    return r["len"] <= TYPED_MAX and not PASTE.match(r["text"])


RELAY = re.compile(FAMILIES["relay_paste"], re.I | re.M)


def cmd_interventions(args):
    rows = [r for r in load(args) if r["source"] in HUMAN]
    for name, pat in FAMILIES.items():
        rx = re.compile(pat, re.I | re.M)
        pool = rows if name == "relay_paste" else [r for r in rows if is_typed(r) and not RELAY.search(r["text"])]
        hits = [r for r in pool if rx.search(r["text"])]
        print(f"## {name}: {len(hits)}")
        for r in tail(hits, args.n):
            print("  " + fmt(r, 160))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def since(s):
        return dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)

    def common(sp, tool=True):
        sp.add_argument("--since", type=since, help="YYYY-MM-DD (UTC)")
        if tool:
            sp.add_argument("--tool", choices=["claude", "pi", "codex", "all"], default="all")
        sp.add_argument("--db", help=f"extracted rows (default {DEFAULT_DB})")

    e = sub.add_parser("extract", help="write one JSONL row per human message")
    e.add_argument("--since", type=since)
    e.add_argument("--tool", choices=["claude", "pi", "codex", "all"], default="all")
    e.add_argument("--out", help=f"output file (default {DEFAULT_DB}); merged like the cache")
    e.add_argument("--rebuild", action="store_true", help="start fresh: drop existing rows (rows from deleted transcripts are lost)")
    e.set_defaults(func=cmd_extract)

    g = sub.add_parser("grep", help="search extracted messages")
    g.add_argument("regex")
    g.add_argument("-C", type=int, default=0, help="show N messages around each hit in the same session")
    common(g)
    g.set_defaults(func=cmd_grep)

    s = sub.add_parser("stats", help="counts, long pastes, duplicates, split pastes, prompt-file pointers")
    common(s)
    s.add_argument("-n", type=int, default=5, help="examples per section")
    s.set_defaults(func=cmd_stats)

    i = sub.add_parser("interventions", help="candidate corrections by regex family")
    common(i)
    i.add_argument("-n", type=int, default=5, help="examples per family")
    i.set_defaults(func=cmd_interventions)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
