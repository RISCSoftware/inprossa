"""Draw a transformer block diagram for the bin packing token encoding."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ── Layout ────────────────────────────────────────────────────────────────────
n_dim = 6
tw    = 0.90   # token column width
ch    = 0.36   # height of one dim-cell
th    = n_dim * ch        # total input-token height = 2.16
hgap  = 0.40              # horizontal gap between tokens
vg1   = 0.60              # gap: input tokens → transformer
tr_h  = 1.50              # transformer block height
vg2   = 0.60              # gap: transformer → output tokens
oh    = 0.72              # output token height

FS    = 20                # uniform font size for all text
ang   = 48                # arrow angle from vertical (degrees)
al    = 0.65 * 0.70       # arrow length (30% shorter than previous)
bbox_pad = 0.07           # must match FancyBboxPatch pad=
adx   = al * np.sin(np.radians(ang))
ady   = al * np.cos(np.radians(ang))

# ── Token data (no padding token) ────────────────────────────────────────────
# bins:  cap 0.8, 0.3, 0.4  +  new-bin slot (cap=1.0)
# items: 0.6 (next↑), 0.6, 0.2
tokens = [
    ([1.0, 0.0, 0.00, 0.0, 0.0, 0.0], 'value'),
    ([0.0, 1.0, 0.80, 0.0, 0.0, 0.0], 'bin'),
    ([0.0, 1.0, 0.30, 0.0, 0.0, 0.0], 'bin'),
    ([0.0, 1.0, 0.40, 0.0, 0.0, 0.0], 'bin'),
    ([0.0, 1.0, 1.00, 0.0, 0.0, 0.0], 'bin'),   # new-bin slot
    ([0.0, 0.0, 0.00, 1.0, 0.6, 1.0], 'item'),  # next item ↑
    ([0.0, 0.0, 0.00, 1.0, 0.6, 0.0], 'item'),
    ([0.0, 0.0, 0.00, 1.0, 0.2, 0.0], 'item'),
]

n_tok = len(tokens)

# Per-dimension colour
dim_fc = ['#AED6F1', '#A9DFBF', '#FAD7A0', '#F1948A', '#D7BDE2', '#A9CCE3']

# X centres
xs = np.array([i * (tw + hgap) for i in range(n_tok)], dtype=float)
xs -= xs.mean()

# Y levels
y0 = 0.0;           y1 = y0 + th          # input token bottom / top
y2 = y1 + vg1;      y3 = y2 + tr_h        # transformer bottom / top
y4 = y3 + vg2;      y5 = y4 + oh          # output token bottom / top

# ── Figure setup ──────────────────────────────────────────────────────────────
margin_l = 0.5
margin_r = 0.5
x_lo = xs[0]  - tw / 2 - margin_l
x_hi = xs[-1] + tw / 2 + margin_r
y_lo = -1.10
y_hi = y5 + ady + 0.65

data_w = x_hi - x_lo
data_h = y_hi - y_lo
scale  = 1.35
fig_w  = data_w * scale
fig_h  = data_h * scale

fig, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.set_xlim(x_lo, x_hi)
ax.set_ylim(y_lo, y_hi)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor('white')

# ── Input tokens ──────────────────────────────────────────────────────────────
for i, (vals, ttype) in enumerate(tokens):
    cx = xs[i]
    for d, v in enumerate(vals):
        ry = y0 + (n_dim - 1 - d) * ch
        fc = dim_fc[d] if v > 0 else '#F5F5F5'
        ax.add_patch(patches.Rectangle(
            (cx - tw / 2, ry), tw, ch,
            lw=0.6, edgecolor='#999', facecolor=fc))
        if v > 0:
            ax.text(cx, ry + ch / 2, f'{v:.1g}',
                    ha='center', va='center', fontsize=FS)

    # Label below each token
    if ttype == 'value':
        lbl = 'value\ntoken';  fc_lbl = '#1A5276'
    elif ttype == 'bin':
        cap = vals[2]
        lbl = 'new\nbin' if cap == 1.0 else f'bin\n({cap:.1f})'
        fc_lbl = '#1E8449'
    else:  # item
        marker = ' ↑' if vals[5] > 0 else ''
        lbl = f'item\n({vals[4]:.1f}){marker}';  fc_lbl = '#6E2F8E'

    ax.text(cx, y0 - 0.08, lbl,
            ha='center', va='top', fontsize=FS, color=fc_lbl)

# ── Arrows: input tokens → transformer ───────────────────────────────────────
for cx in xs:
    ax.annotate('', xy=(cx, y2 - bbox_pad), xytext=(cx, y1),
                arrowprops=dict(arrowstyle='->', color='#555', lw=1.8,
                                mutation_scale=13, shrinkA=0, shrinkB=0))

# ── Transformer block ─────────────────────────────────────────────────────────
tx0 = xs[0]  - tw / 2 - 0.25
txw = xs[-1] + tw / 2 + 0.25 - tx0
ax.add_patch(patches.FancyBboxPatch(
    (tx0, y2), txw, tr_h,
    boxstyle=f'round,pad={bbox_pad}', lw=2.0,
    edgecolor='#1A252F', facecolor='#EBF5FB'))
ax.text(tx0 + txw / 2, y2 + tr_h / 2, 'Transformer',
        ha='center', va='center', fontsize=FS, fontweight='bold', color='#1A252F')

# ── Arrows: transformer → output tokens ──────────────────────────────────────
for cx in xs:
    ax.annotate('', xy=(cx, y4), xytext=(cx, y3 + bbox_pad),
                arrowprops=dict(arrowstyle='->', color='#555', lw=1.8,
                                mutation_scale=13, shrinkA=0, shrinkB=0))

# ── Output tokens ─────────────────────────────────────────────────────────────
for cx in xs:
    ax.add_patch(patches.Rectangle(
        (cx - tw / 2, y4), tw, oh,
        lw=1.4, edgecolor='#2C3E50', facecolor='white'))

# ── Forked arrows from each output token ─────────────────────────────────────
bin_idx = 0   # counter for u_1 … u_4
lbl_off = 0.06
for i, (_, ttype) in enumerate(tokens):
    cx = xs[i]
    src   = (cx, y5)
    dst_l = (cx - adx, y5 + ady)
    dst_r = (cx + adx, y5 + ady)

    # left arrow
    if ttype == 'value':
        kw = dict(arrowstyle='->', color='#1A5276', lw=1.8, mutation_scale=13, shrinkA=0, shrinkB=0)
    else:
        kw = dict(arrowstyle='->', color='#CCCCCC', lw=0.9, mutation_scale=9,  shrinkA=0, shrinkB=0)
    ax.annotate('', xy=dst_l, xytext=src, arrowprops=kw)
    if ttype == 'value':
        ax.text(dst_l[0] - lbl_off, dst_l[1], r'$v$',
                ha='right', va='center', fontsize=FS,
                color='#1A5276', fontweight='bold')

    # right arrow
    if ttype == 'bin':
        kw = dict(arrowstyle='->', color='#1E8449', lw=1.8, mutation_scale=13, shrinkA=0, shrinkB=0)
    else:
        kw = dict(arrowstyle='->', color='#CCCCCC', lw=0.9, mutation_scale=9,  shrinkA=0, shrinkB=0)
    ax.annotate('', xy=dst_r, xytext=src, arrowprops=kw)
    if ttype == 'bin':
        bin_idx += 1
        ax.text(dst_r[0] + lbl_off, dst_r[1], f'$u_{bin_idx}$',
                ha='left', va='center', fontsize=FS,
                color='#1E8449', fontweight='bold')

plt.tight_layout(pad=0.2)
out = 'transformer_diagram.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved {out}')
