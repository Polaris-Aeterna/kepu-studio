"""style.py text helpers: Unicode super/subscripts, sup_markup spans, the episode table.  (imports ManimGL)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style  # noqa: E402


def test_detects_unicode_scripts():
    assert style.has_unicode_scripts("Aₜ")
    assert style.has_unicode_scripts("(−1)ʲ")
    assert style.has_unicode_scripts("T²")
    assert not style.has_unicode_scripts("普通文字 x_1 2^n")


def test_unicode_scripts_markup_spans():
    m = style.unicode_scripts_markup("Aₜ 与 (−1)ʲ & <x>")
    assert "baseline_shift='superscript'>j</span>" in m
    assert "rise='-4000'>t</span>" in m
    assert "&amp;" in m and "&lt;x&gt;" in m


def test_sup_markup_attribute_names_untouched():
    """_x rewriting must not hit 'baseline_shift' inside an inserted span (2026-10-28 bug)."""
    m = style.sup_markup("2^{o(n)} 与 x_{12}，T²", span=True)
    assert "baseline_shift='superscript'>o(n)</span>" in m
    assert "rise='-4000'>12</span>" in m
    assert "baseline<span" not in m
    assert style.sup_markup("A 2^{o(n)} x_1") == "A 2<sup>o(n)</sup> x<sub>1</sub>"


def test_episode_table_matches_chapter_cards():
    assert set(style.EPISODES) == {1, 2, 3, 4, 5, 6}
    assert style.episode_en(3) == "EPISODE 3    Forty Years of Bases"
    assert style.episode_en(4) == "EPISODE 4    The Wager"
