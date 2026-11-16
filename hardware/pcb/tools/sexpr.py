"""Minimal S-expression reader/writer for KiCad files + library symbol helpers."""
import re
import copy

TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


class Sym(str):
    """Bare (unquoted) token."""


def _unq(t):
    out = []
    i = 0
    while i < len(t):
        c = t[i]
        if c == '\\' and i + 1 < len(t):
            n = t[i + 1]
            out.append({'n': '\n', 't': '\t'}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def parse(s):
    stack = [[]]
    for m in TOK.finditer(s):
        t = m.group(1)
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif t.startswith('"'):
            stack[-1].append(_unq(t[1:-1]))
        else:
            stack[-1].append(Sym(t))
    return stack[0]


def q(s):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '"' + s + '"'


def fmt_num(x):
    if isinstance(x, float):
        r = ('%.4f' % x).rstrip('0').rstrip('.')
        return '0' if r in ('-0', '') else r
    return str(x)


def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return '()'
        simple = all(not isinstance(e, list) for e in x)
        if simple and len(x) < 14:
            return '(' + ' '.join(dump(e) for e in x) + ')'
        out = '(' + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                out += '\n' + '\t' * (ind + 1) + dump(e, ind + 1)
            else:
                out += ' ' + dump(e)
        return out + '\n' + '\t' * ind + ')'
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, (int, float)):
        return fmt_num(x)
    return q(x)


def find(x, key):
    return [e for e in x if isinstance(e, list) and e and e[0] == key]


def find1(x, key):
    r = find(x, key)
    return r[0] if r else None


LIBDIR = r"C:/Program Files/KiCad/10.0/share/kicad/symbols/"
_cache = {}


def load_lib(lib):
    if lib not in _cache:
        path = lib if lib.endswith('.kicad_sym') else LIBDIR + lib + '.kicad_sym'
        _cache[lib] = parse(open(path, encoding='utf-8').read())[0]
    return _cache[lib]


def get_symbol(lib, name):
    """Return a flattened (no 'extends') deep copy of symbol `name`."""
    L = load_lib(lib)
    syms = {s[1]: s for s in find(L, 'symbol')}
    s = syms[name]
    ext = find1(s, 'extends')
    if not ext:
        return copy.deepcopy(s)
    parent = get_symbol(lib, ext[1])
    childprops = {pr[1]: pr for pr in find(s, 'property')}
    newp = [parent[0], name]
    for e in parent[2:]:
        if isinstance(e, list) and e and e[0] == 'property' and e[1] in childprops:
            newp.append(copy.deepcopy(childprops.pop(e[1])))
        elif isinstance(e, list) and e and e[0] == 'symbol':
            e = copy.deepcopy(e)
            e[1] = name + e[1][len(parent[1]):]
            newp.append(e)
        else:
            newp.append(copy.deepcopy(e))
    idx = max(i for i, e in enumerate(newp) if isinstance(e, list) and e and e[0] == 'property')
    for pr in childprops.values():
        idx += 1
        newp.insert(idx, copy.deepcopy(pr))
    return newp


def pins(symdef):
    out = []
    for sub in find(symdef, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', sub[1])
        unit = int(m.group(1))
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            ln = find1(p, 'length')
            nm = find1(p, 'name')
            nb = find1(p, 'number')
            h = find1(p, 'hide')
            hidden = ('hide' in [e for e in p if isinstance(e, Sym)]) or (h is not None and len(h) > 1 and h[1] == 'yes')
            out.append(dict(unit=unit, type=str(p[1]), num=nb[1], name=nm[1],
                            x=float(at[1]), y=float(at[2]), ang=float(at[3]),
                            len=float(ln[1]), hidden=hidden))
    return out
