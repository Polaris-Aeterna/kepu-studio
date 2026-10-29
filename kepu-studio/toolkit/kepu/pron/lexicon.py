"""三层读音词典：插件内置 < 个人全局（~/.kepu/lexicon.tsv）< 项目（pron/lexicon.tsv）。

每行一条：`词条（带读音标记）<TAB>动作<TAB>备注`。
    方差〔chā〕              force   统计：方差、协方差
    长〔cháng〕子句           force   分词陷阱：长子 + 句
    了〔liǎo〕解              leave   常用词，模型稳定（定了读音，但不换替身字）
    分量                      hold    同形词：重量 fèn / 分量 fēn，稿子里必须标
动作：force（默认）= 换成替身字；leave = 只记下决定、不改文字；hold = 每次都拦下，要求在稿子里标读音。
匹配取最长的词条；两个词条在同一个字上给出不同读音、又互不包含 → 冲突，拦下。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..util import DATA, USER_DIR, read_tsv
from .inventory import polyphones, readings_of
from .marks import parse_marks

LAYERS = ("builtin", "user", "project")
ACTIONS = ("force", "leave", "hold")


@dataclass
class Entry:
    clean: str
    readings: dict            # position in clean -> reading
    action: str = "force"
    note: str = ""
    layer: str = "builtin"
    where: str = ""

    @property
    def spec(self) -> str:
        return "".join(c + (f"〔{self.readings[k]}〕" if k in self.readings else "") for k, c in enumerate(self.clean))


@dataclass
class Hit:
    reading: str
    action: str
    entry: Entry
    start: int
    conflicts: list = field(default_factory=list)


def parse_entry(spec: str, action: str = "force", note: str = "", layer: str = "project", where: str = ""):
    """'长〔cháng〕子句' -> Entry; raises ValueError for an impossible reading."""
    clean, marks = parse_marks(spec.strip())
    if not clean:
        raise ValueError("空词条")
    action = (action or "force").strip() or "force"
    if action not in ACTIONS:
        raise ValueError(f"动作必须是 {'/'.join(ACTIONS)}：{action}")
    for k, r in marks.items():
        if r == "?":                 # 分〔?〕量 is how a hold entry is written back (add_entry, find)
            if action != "hold":
                raise ValueError(f"“{clean[k]}〔?〕”只能用在 hold 词条里")
            continue
        rs = readings_of(clean[k])
        if rs and r not in rs:
            raise ValueError(f"“{clean[k]}”没有读音 {r}（可选：{'、'.join(rs)}）")
    if action == "hold" and not marks:
        marks = {k: "?" for k, c in enumerate(clean) if c in polyphones()}
    if not marks:
        raise ValueError(f"词条“{spec}”没有标任何读音（例：方差〔chā〕）")
    return Entry(clean, marks, action, note.strip(), layer, where)


def layer_path(layer: str, project_root: Path | None) -> Path | None:
    if layer == "builtin":
        return DATA / "lexicon.tsv"
    if layer == "user":
        return USER_DIR / "lexicon.tsv"
    return (project_root / "pron" / "lexicon.tsv") if project_root else None


class Lexicon:
    def __init__(self, project_root: Path | None = None, user: bool = True, builtin: bool = True):
        self.project_root = project_root
        self.entries: list[Entry] = []
        self.errors: list[str] = []
        for layer in LAYERS:
            if (layer == "user" and not user) or (layer == "builtin" and not builtin):
                continue
            p = layer_path(layer, project_root)
            if not p or not p.exists():
                continue
            for n, row in enumerate(read_tsv(p), 1):
                try:
                    self.entries.append(parse_entry(row[0], row[1] if len(row) > 1 else "force",
                                                    row[2] if len(row) > 2 else "", layer, f"{p.name}:{n}"))
                except ValueError as e:
                    self.errors.append(f"{p}: {row[0]}: {e}")
        # the same word in a higher layer replaces the lower one
        best: dict[str, Entry] = {}
        for e in self.entries:
            if e.clean not in best or LAYERS.index(e.layer) >= LAYERS.index(best[e.clean].layer):
                best[e.clean] = e
        self.by_first: dict[str, list[Entry]] = {}
        for e in best.values():
            self.by_first.setdefault(e.clean[0], []).append(e)

    def occurrences(self, text: str) -> list[tuple[int, Entry]]:
        out = []
        for s, ch in enumerate(text):
            for e in self.by_first.get(ch, ()):
                if text.startswith(e.clean, s):
                    out.append((s, e))
        return out

    def covering(self, text: str) -> dict[int, list[tuple[int, Entry]]]:
        """position -> every (start, entry) whose marks cover it."""
        cover: dict[int, list[tuple[int, Entry]]] = {}
        for s, e in self.occurrences(text):
            for k in e.readings:
                cover.setdefault(s + k, []).append((s, e))
        return cover

    def decide(self, text: str) -> dict[int, Hit]:
        """position -> Hit from the longest covering entries; conflicts listed on the hit."""
        cover: dict[int, list[tuple[int, Entry]]] = {}
        for s, e in self.occurrences(text):
            for k in e.readings:
                cover.setdefault(s + k, []).append((s, e))
        out = {}
        for i, occ in cover.items():
            spans = [(s, s + len(e.clean), e) for s, e in occ]
            maximal = [x for x in spans if not any((a <= x[0] and x[1] <= b and (a, b) != (x[0], x[1]))
                                                   for a, b, _ in spans)]
            maximal.sort(key=lambda x: (x[1] - x[0], LAYERS.index(x[2].layer)), reverse=True)
            s, _, e = maximal[0]
            hit = Hit(e.readings[i - s], e.action, e, s)
            for s2, _, e2 in maximal[1:]:
                r2 = e2.readings[i - s2]
                if r2 != hit.reading or e2.action != hit.action:
                    hit.conflicts.append(e2)
            out[i] = hit
        return out

    def find(self, query: str) -> list[Entry]:
        return [e for es in self.by_first.values() for e in es if query in e.clean]


def add_entry(spec: str, action: str = "force", note: str = "", scope: str = "project",
              project_root: Path | None = None) -> tuple[Entry, Path]:
    """Append (or replace) an entry in the project or user lexicon.  Returns (entry, file)."""
    if scope not in ("project", "user"):
        raise ValueError("scope 只能是 project 或 user")
    path = layer_path(scope, project_root)
    if path is None:
        raise ValueError("不在 kepu 项目里（找不到 kepu.toml），用 --scope user 写进个人词典")
    e = parse_entry(spec, action, note, scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else [
        "# 项目读音词典（kepu）。每行：词条（带读音标记）<TAB>动作 force|leave|hold<TAB>备注。只增改，不删别人的条目。"]
    keep = [ln for ln in lines if not (ln and not ln.startswith("#") and parse_marks(ln.split("\t")[0])[0] == e.clean)]
    keep.append(f"{e.spec}\t{e.action}\t{e.note}")
    path.write_text("\n".join(keep) + "\n", encoding="utf-8")
    return e, path
