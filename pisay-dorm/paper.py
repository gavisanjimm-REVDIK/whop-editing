"""Procedural crumpled-paper look + the 'crumpled paper opening' transition.

Paper space is the full frame (W x H). A Voronoi crease height field is lit to look like
creased paper. The crumple amount (a) scales the slopes: BALL = tight ball, REST = flattened
sheet with leftover wrinkles (that's the look of every text-only card).

Card content is a white RGB "ink" image that is MULTIPLIED onto the paper, so text and
highlighter look printed and pick up the wrinkle shading.
"""
import math

import cv2
import numpy as np
from scipy.spatial import cKDTree

W, H = 1920, 1080
REST = 0.07          # wrinkle amount left on an opened sheet
BALL = 0.58          # wrinkle amount when balled up
LIGHT = np.array([-0.45, -0.60, 0.66])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _voronoi(n, rng, margin=0.15):
    pts = np.column_stack([rng.uniform(-margin * W, (1 + margin) * W, n),
                           rng.uniform(-margin * H, (1 + margin) * H, n)])
    yy, xx = np.mgrid[0:H, 0:W]
    q = np.column_stack([xx.ravel(), yy.ravel()]).astype(np.float32)
    d, i = cKDTree(pts).query(q, k=2, workers=-1)
    return i[:, 0].reshape(H, W), (d[:, 1] - d[:, 0]).reshape(H, W).astype(np.float32)


def _noise(rng, shape, scale):
    small = rng.standard_normal((max(2, shape[0] // scale), max(2, shape[1] // scale))).astype(np.float32)
    return cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)


class Paper:
    def __init__(self, seed=7, lined=True):
        rng = np.random.default_rng(seed)
        # crease height field: each Voronoi cell is a "tent" rising from its borders with a
        # random sign/height, so cell borders become sharp ridges and valleys (crumple creases)
        i1, g1 = _voronoi(110, rng)
        i2, g2 = _voronoi(600, rng)
        s1 = rng.uniform(-1, 1, i1.max() + 1).astype(np.float32)
        s2 = rng.uniform(-1, 1, i2.max() + 1).astype(np.float32)
        h = np.minimum(g1, 140) * s1[i1] + np.minimum(g2, 50) * s2[i2] * 0.5
        h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 1.2)
        gy, gx = np.gradient(h)
        zero = np.zeros_like(gx)
        self.fields = np.dstack([gx, gy, zero, zero]).astype(np.float32)

        # paper colour, blotches and grain
        base = np.array([241, 237, 226], np.float32)
        blot = _noise(rng, (H, W), 90) * 3.0 + _noise(rng, (H, W), 12) * 1.5
        grain = rng.normal(0, 2.2, (H, W)).astype(np.float32)
        tex = base[None, None, :] + (blot + grain)[..., None]
        if lined:  # faint notebook paper: blue rules + red margin
            for y in range(150, H, 58):
                tex[y:y + 2, :, :] = tex[y:y + 2, :, :] * 0.55 + np.array([150, 185, 225]) * 0.45
            tex[:, 168:171, :] = tex[:, 168:171, :] * 0.45 + np.array([225, 110, 110]) * 0.55
        self.tex = np.clip(tex, 0, 255).astype(np.float32)

        # flat card = paper at rest wrinkle
        self.rest = self.tex * self._shade(self.fields, REST)[..., None]

    @staticmethod
    def _shade(f, a):
        nx, ny = -a * f[..., 0], -a * f[..., 1]
        s = (nx * LIGHT[0] + ny * LIGHT[1] + LIGHT[2]) / np.sqrt(nx * nx + ny * ny + 1) / LIGHT[2]
        return np.clip(0.35 + 0.65 * s, 0.25, 1.2).astype(np.float32)

    def card(self, ink):
        """Flat sheet with content. ink: HxWx3 uint8/float (white = no ink)."""
        return self.rest * (ink.astype(np.float32) / 255.0)

    def sticker_patch(self, w, h, x0=300, y0=200):
        """A crop of the rest-paper (unlined look comes from tex rows chosen by caller)."""
        return self.rest[y0:y0 + h, x0:x0 + w]

    # ------------------------------------------------------------------ transition
    def frame(self, bg, ink, e, ball_r=150, center=(W / 2, H / 2), theta=0.0, ball=0.0,
              seed=3):
        """Render one frame of a (un)crumpling sheet over bg.

        e      unfold progress 0 (ball) .. 1 (flat full-frame sheet)
        ball_r radius of the ball in px when e = 0 (scaled by `ball` pop-in)
        theta  rotation (deg)
        """
        e = float(np.clip(e, 0, 1))
        if e >= 0.999:
            return self.card(ink)
        a = REST + (BALL - REST) * (1 - e) ** 1.25
        n = 2.0 + 30.0 * e ** 1.6
        amp = 0.20 * (1 - e) ** 1.3
        hw = ball_r + (W / 2 - ball_r) * e
        hh = ball_r + (H / 2 - ball_r) * e
        cx = center[0] + (W / 2 - center[0]) * e
        cy = center[1] + (H / 2 - center[1]) * e
        th = math.radians(theta) * (1 - e) ** 2

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dx, dy = xx - cx, yy - cy
        c, s = math.cos(-th), math.sin(-th)
        u = (dx * c - dy * s) / hw
        v = (dx * s + dy * c) / hh
        au, av = np.abs(u) + 1e-6, np.abs(v) + 1e-6
        rho = (au ** n + av ** n) ** (1.0 / n)
        ang = np.arctan2(v, u)
        rng = np.random.default_rng(seed)
        edge = np.ones_like(rho)
        for k in (3, 5, 7, 11, 13):
            edge += amp * rng.uniform(0.4, 1.0) / math.sqrt(k) * np.sin(k * ang + rng.uniform(0, 6.28))
        edge *= 1.0 + 0.04 * e
        aa = 1.5 / min(hw, hh)
        mask = np.clip((edge - rho) / aa + 0.5, 0, 1)

        # paper-space coords
        px = (W / 2 + u * W / 2).astype(np.float32)
        py = (H / 2 + v * H / 2).astype(np.float32)
        f = cv2.remap(self.fields, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        tex = cv2.remap(self.tex, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        off = 40.0 * (a - REST)  # content fractures along facets while crumpled
        ink_s = cv2.remap(ink.astype(np.float32), px + off * f[..., 0], py + off * f[..., 1],
                          cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        shade = self._shade(f, a)
        if e < 1:  # round-ball shading while still balled up
            d = np.clip(rho / edge, 0, 1)
            shade *= 1 - (1 - e) ** 2 * (0.55 * d ** 2)
        paper = tex * shade[..., None] * (ink_s / 255.0)

        # soft drop shadow on the background
        sm = cv2.resize(mask, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        sh_off = int(4 + 6 * (1 - e))
        sm = np.roll(np.roll(sm, sh_off, 0), sh_off, 1)
        sm = cv2.GaussianBlur(sm, (0, 0), 6)
        sh = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
        out = bg.astype(np.float32) * (1 - 0.55 * sh[..., None])
        m = mask[..., None]
        return out * (1 - m) + paper * m
