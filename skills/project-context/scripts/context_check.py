#!/usr/bin/env python3
"""Check a Markdown context registry; silent when no defects are found."""
from __future__ import annotations
import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ID = re.compile(r'\bD-\d{3,}\b')
HEADING = re.compile(r'^#{1,6}\s+(D-\d{3,})\b[^\n]*', re.M)
LINK = re.compile(r'\]\(([^)]+)\)')

def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ''

def entries(text):
    matches = list(HEADING.finditer(text))
    output = {}
    for i, match in enumerate(matches):
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        # Metadata may legitimately change; the decision line itself may not.
        statement = re.search(r'^\s*[-*]\s*(?:Decision|Statement):\s*(.*(?:\n[ \t]+(?![-*]\s)[^\n]+)*)', body, re.I | re.M)
        if statement:
            output[match.group(1)] = ' '.join(statement.group(1).split())
    return output

def check(root, count, base=None, excludes=(), history_commits=100):
    context = root / 'project-context'
    registry = context / 'DECISIONS.md'
    text = registry.read_text(encoding='utf-8') if registry.is_file() else ''
    known = set(HEADING.findall(text))
    findings = []
    in_git = bool(git(root, 'rev-parse', '--show-toplevel'))
    if base and (not in_git or not git(root, 'rev-parse', '--verify', base + '^{commit}')):
        raise ValueError(f'cannot resolve Git base {base}; fetch the required history or choose an available revision')
    paths = set(filter(None, git(root, 'ls-files', '-z').split('\0')))
    paths.update(filter(None, git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')))
    if not in_git:
        paths.update(path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file() and not path.is_symlink() and '.git' not in path.relative_to(root).parts)
    for name in sorted(paths):
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in excludes):
            continue
        path = root / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
            if b'\0' in data:
                continue
            lines = data.decode('utf-8').splitlines()
        except (UnicodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            definition = HEADING.match(line) if path == registry else None
            for match in ID.finditer(line):
                if definition and match.start() == definition.start(1):
                    continue
                decision = match.group()
                if decision not in known:
                    findings.append(f'{name}:{number}: decision {decision} is absent from project-context/DECISIONS.md')
            if path.parent == context and path.name in {'DECISIONS.md', 'LEARNINGS.md', 'NOW.md'}:
                for match in LINK.finditer(line):
                    destination = unquote(match.group(1).split('#', 1)[0].split('?', 1)[0])
                    if not destination or '://' in destination or destination.startswith('/'):
                        continue
                    resolved = (path.parent / destination).resolve()
                    roots = [(root / 'docs/agent_logs').resolve(), (context / 'decisions').resolve(), (context / 'incidents').resolve()]
                    if any(resolved == directory or directory in resolved.parents for directory in roots) and not resolved.exists():
                        findings.append(f'{name}:{number}: broken link {destination}')
    def compare(old, new):
        new_entries = entries(new)
        for key, statement in entries(old).items():
            if key not in new_entries or new_entries[key] != statement:
                heading = next((m for m in HEADING.finditer(text) if m.group(1) == key), None)
                number = text[:heading.start()].count('\n') + 1 if heading else 1
                finding = f'project-context/DECISIONS.md:{number}: {key} statement changed; supersede it instead'
                if finding not in findings:
                    findings.append(finding)
    if in_git and git(root, 'rev-parse', '--verify', 'HEAD'):
        if base:
            compare(git(root, 'show', f'{base}:project-context/DECISIONS.md'), text)
        else:
            # Inspect adjacent first-parent revisions so an edit remains visible
            # after unrelated commits; the window is bounded for large repos.
            commits = git(root, 'rev-list', '--first-parent', f'--max-count={history_commits}', 'HEAD').splitlines()
            newer = text
            for commit in commits:
                older = git(root, 'show', f'{commit}:project-context/DECISIONS.md')
                compare(older, newer)
                newer = older
        commits = git(root, 'log', '--first-parent', '--format=%H%x09%s').splitlines()
        prs = [line.split('\t', 1)[0] for line in commits if re.search(r'(?:Merge pull request #\d+|\(#\d+\))', line)]
        if len(prs) >= count:
            changed = [set(git(root, 'diff-tree', '--no-commit-id', '--name-only', '-r', '-m', '--first-parent', commit).splitlines()) for commit in prs[:count]]
            now = 'project-context/NOW.md'
            if all(now not in files for files in changed) and any({'project-context/DECISIONS.md', 'project-context/LEARNINGS.md'} & files for files in changed):
                findings.append(f'{now}:1: unchanged across {count} merged PRs while decisions or learnings changed')
    return findings

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path('.'))
    parser.add_argument('--merged-prs', type=int, default=5)
    parser.add_argument('--base', help='compare decision statements with this Git revision')
    parser.add_argument('--history-commits', type=int, default=100, help='number of first-parent revisions to inspect (default 100)')
    parser.add_argument('--exclude', action='append', default=[], help='exclude a repository-relative glob containing examples')
    args = parser.parse_args(argv)
    if args.merged_prs < 1 or args.history_commits < 1:
        parser.error('--merged-prs and --history-commits must be positive')
    root = args.target.resolve()
    try:
        findings = check(root, args.merged_prs, args.base, args.exclude, args.history_commits)
    except ValueError as error:
        print(f'project-context/DECISIONS.md:1: {error}', file=sys.stderr)
        return 2
    if git(root, 'rev-parse', '--is-shallow-repository').strip() == 'true':
        print('project-context/DECISIONS.md:1: shallow Git history; earlier decision edits and PRs may be unavailable', file=sys.stderr)
    for finding in findings:
        print(finding)
    return bool(findings)

if __name__ == '__main__':
    raise SystemExit(main())
