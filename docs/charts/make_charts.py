"""Draw the README's charts as static SVGs.

    python3 docs/charts/make_charts.py

Numbers are read from benchmarks/data/committee/scores_v2.json (written by benchmarks/score_committee.py): the
2,000 random works, committee labels, unresolved pairs counted as no, each classifier at its served threshold. The
tables in benchmarks/data/committee/scores_v2.md carry the same numbers, so the charts can be checked against them.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "img"

# One version per chart that reads on GitHub's light (#ffffff) and dark (#0d1117) pages alike. Text #707a84 is 4.4:1 on
# both; the two bar colors clear 3:1 on both and stay apart for the common color-vision deficiencies.
THEME = dict(ink="#707a84", grid="#8b949e", old="#199e70", new="#2a78d6")
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
NAMES = {1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education", 5: "Gender equality",
         6: "Clean water and sanitation", 7: "Affordable and clean energy", 8: "Decent work and economic growth",
         9: "Industry, innovation and infrastructure", 10: "Reduced inequalities", 11: "Sustainable cities and communities",
         12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water", 15: "Life on land",
         16: "Peace, justice, and strong institutions", 17: "Partnerships for the goals"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts, self.title = w, h, [], title

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, fill, size=14, anchor="start", weight=400):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" dominant-baseline="middle">{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke, opacity=0.35):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="1" stroke-opacity="{opacity}"/>')

    def save(self, path):
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'role="img" font-family=\'{FONT}\' style="font-variant-numeric: tabular-nums">\n'
            f'<title>{esc(self.title)}</title>\n' + "\n".join(self.parts) + "\n</svg>\n")


def hbar(x0, y, w, h, r=4):
    """Bar from the baseline x0, square at the baseline, rounded at the data end."""
    if w < 0.5:
        return ""
    r = min(r, w / 2, h / 2)
    return (f"M{x0:.1f},{y:.1f} H{x0 + w - r:.1f} Q{x0 + w:.1f},{y:.1f} {x0 + w:.1f},{y + r:.1f} "
            f"V{y + h - r:.1f} Q{x0 + w:.1f},{y + h:.1f} {x0 + w - r:.1f},{y + h:.1f} H{x0:.1f} Z")


def legend(s, x, y, items, t):
    for label, color in items:
        s.add(f'<rect x="{x}" y="{y - 6}" width="12" height="12" rx="2" fill="{color}"/>')
        s.text(x + 18, y, label, t["ink"], 14)
        x += 18 + len(label) * 7.6 + 26


def grouped(t, title, rows, series):
    """Grouped horizontal bars on a visible 0-100% scale, one row per goal; the first row (all goals) is set apart."""
    W, L, R, bh, gap, pad = 760, 322, 46, 12, 3, 16
    n = len(series)
    top = 62
    rowH = n * bh + (n - 1) * gap + pad
    H = top + len(rows) * rowH + 14
    s = Svg(W, H, title)
    x = lambda v: L + v / 100 * (W - L - R)
    legend(s, 0, 14, series, t)
    for tick in (0, 25, 50, 75, 100):
        s.line(x(tick), top - 12, x(tick), H - 4, t["grid"], opacity=0.8 if tick == 0 else 0.35)
        s.text(x(tick), top - 22, f"{tick}%", t["ink"], 12, "middle")
    for i, (label, vals) in enumerate(rows):
        y0 = top + i * rowH + pad / 2 + (10 if i else 0)
        cy = y0 + (n * bh + (n - 1) * gap) / 2
        s.text(0, cy, label, t["ink"], 14, weight=700 if i == 0 else 500)
        for j, v in enumerate(vals):
            y = y0 + j * (bh + gap)
            s.add(f'<path d="{hbar(x(0), y, x(v) - x(0), bh)}" fill="{series[j][1]}"/>')
            s.text(x(v) + 6, y + bh / 2, f"{v:.0f}%", t["ink"], 12, weight=600 if j == n - 1 else 400)
        if i == 0:
            s.line(0, y0 + n * bh + (n - 1) * gap + pad / 2 + 5, W - 4, y0 + n * bh + (n - 1) * gap + pad / 2 + 5, t["grid"], opacity=0.5)
    return s


def main():
    t = THEME
    OUT.mkdir(exist_ok=True)
    res = json.loads((ROOT / "benchmarks/data/committee/scores_v2.json").read_text())["sets"]["s2"]["brackets"]["no"]
    pooled, per = res["pooled"], res["per_goal"]
    series = [("Old: Aurora SDG-BERT", t["old"]), ("New: OpenAlex head v2", t["new"])]
    words = {"P": "Precision", "R": "Recall", "F1": "F1"}
    for k, fname in (("F1", "f1-by-goal.svg"), ("P", "precision-by-goal.svg"), ("R", "recall-by-goal.svg")):
        rows = [("All 17 goals", [100 * (pooled["aurora"][k] or 0), 100 * (pooled["head"][k] or 0)])]
        rows += [(f"{g} {NAMES[g]}", [100 * (per[str(g)]["aurora"][k] or 0), 100 * (per[str(g)]["head"][k] or 0)])
                 for g in range(1, 18)]
        grouped(t, f"{words[k]} by goal on 2,000 random OpenAlex works, judged by a committee of AI models: "
                   "the old classifier and the new one", rows, series).save(OUT / fname)
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
