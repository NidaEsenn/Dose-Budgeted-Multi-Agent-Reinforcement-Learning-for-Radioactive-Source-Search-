"""Fused Numba kernels for the hot path (wall optical depth for B x P x N rays).

Numerically identical to :func:`radsearch.physics.wall_optical_depth` (tested in
tests/test_kernels.py); chosen after benchmarking against NumPy and torch
(docs/DESIGN_DECISIONS.md, D2).
"""
import numpy as np

try:
    import numba as nb
    HAVE_NUMBA = True
except ImportError:  # pragma: no cover
    HAVE_NUMBA = False


def _tau_bpn_py(src, det, rects, mu, nrect, height):
    from . import physics as P
    K = rects.shape[1]
    out = P.wall_optical_depth(src[:, :, None, :], det[:, None, :, :],
                               rects[:, None, None, :, :], mu[:, None, None, :], height)
    return out


if HAVE_NUMBA:
    @nb.njit(parallel=True, fastmath=False, cache=True)
    def _tau_bpn_nb(src, det, rects, mu, nrect, height):
        B, Pn = src.shape[0], src.shape[1]
        N = det.shape[1]
        out = np.zeros((B, Pn, N))
        h2 = height * height
        for b in nb.prange(B):
            nk = nrect[b]
            if nk == 0:
                continue
            for p in range(Pn):
                sx = src[b, p, 0]
                sy = src[b, p, 1]
                for n in range(N):
                    dx = det[b, n, 0] - sx
                    dy = det[b, n, 1] - sy
                    tau = 0.0
                    for k in range(nk):
                        m = mu[b, k]
                        if m == 0.0:
                            continue
                        x0 = rects[b, k, 0]; y0 = rects[b, k, 1]
                        x1 = rects[b, k, 2]; y1 = rects[b, k, 3]
                        te = 0.0
                        tx = 1.0
                        if dx == 0.0:
                            if sx < x0 or sx > x1:
                                continue
                        else:
                            a = (x0 - sx) / dx
                            c = (x1 - sx) / dx
                            if a > c:
                                a, c = c, a
                            te = max(te, a)
                            tx = min(tx, c)
                        if dy == 0.0:
                            if sy < y0 or sy > y1:
                                continue
                        else:
                            a = (y0 - sy) / dy
                            c = (y1 - sy) / dy
                            if a > c:
                                a, c = c, a
                            te = max(te, a)
                            tx = min(tx, c)
                        if tx > te:
                            tau += m * (tx - te)
                    if tau > 0.0:
                        d2sq = dx * dx + dy * dy
                        # chord (t-units) * |d2| * d3/d2 = t * d3
                        tau *= np.sqrt(d2sq + h2)
                    out[b, p, n] = tau
        return out


def tau_bpn(src, det, rects, mu, nrect, height):
    """Optical depth for every (env b, particle p, robot n).

    src (B,P,2), det (B,N,2), rects (B,K,4), mu (B,K) zero-padded, nrect (B,) int.
    """
    if HAVE_NUMBA:
        return _tau_bpn_nb(np.ascontiguousarray(src, dtype=np.float64),
                           np.ascontiguousarray(det, dtype=np.float64),
                           np.ascontiguousarray(rects, dtype=np.float64),
                           np.ascontiguousarray(mu, dtype=np.float64),
                           np.ascontiguousarray(nrect, dtype=np.int64), float(height))
    return _tau_bpn_py(src, det, rects, mu, nrect, height)


if HAVE_NUMBA:
    @nb.njit(parallel=True, cache=True)
    def _loglik_bp_nb(src, logA, det, counts, active, rects, mu, nrect, height, mu_air,
                      k_det, r2, fit_m, bkg, dead, dwell, sig2):
        """Fused tau -> expected counts -> Poisson log-lik, summed over robots."""
        B, Pn = src.shape[0], src.shape[1]
        N = det.shape[1]
        out = np.zeros((B, Pn))
        h2 = height * height
        for b in nb.prange(B):
            nk = nrect[b]
            for p in range(Pn):
                sx = src[b, p, 0]
                sy = src[b, p, 1]
                A = 10.0 ** logA[b, p]
                acc = 0.0
                for n in range(N):
                    if active[b, n] == 0.0:
                        continue
                    dx = det[b, n, 0] - sx
                    dy = det[b, n, 1] - sy
                    tau = 0.0
                    for k in range(nk):
                        m = mu[b, k]
                        if m == 0.0:
                            continue
                        x0 = rects[b, k, 0]; y0 = rects[b, k, 1]
                        x1 = rects[b, k, 2]; y1 = rects[b, k, 3]
                        te = 0.0
                        tx = 1.0
                        if dx == 0.0:
                            if sx < x0 or sx > x1:
                                continue
                        else:
                            a = (x0 - sx) / dx
                            c = (x1 - sx) / dx
                            if a > c:
                                a, c = c, a
                            te = max(te, a)
                            tx = min(tx, c)
                        if dy == 0.0:
                            if sy < y0 or sy > y1:
                                continue
                        else:
                            a = (y0 - sy) / dy
                            c = (y1 - sy) / dy
                            if a > c:
                                a, c = c, a
                            te = max(te, a)
                            tx = min(tx, c)
                        if tx > te:
                            tau += m * (tx - te)
                    d3 = np.sqrt(dx * dx + dy * dy + h2)
                    tau *= d3
                    geo = 0.5 * (1.0 - d3 / np.sqrt(r2 + fit_m * d3 + d3 * d3))
                    rate = A * k_det * geo * np.exp(-mu_air * d3 - tau) + bkg
                    if dead > 0.0:
                        rate = rate / (1.0 + rate * dead)
                    lam = max(rate * dwell, 1e-12)
                    if sig2 > 0.0:
                        v = sig2 + 1.0 / (lam + 0.5)
                        r = np.log(counts[b, n] + 0.5) - np.log(lam + 0.5)
                        acc += -0.5 * r * r / v - 0.5 * np.log(v)
                    else:
                        acc += counts[b, n] * np.log(lam) - lam
                out[b, p] = acc
        return out


def loglik_bp(src, logA, det_xy, counts, active, rects, mu, nrect, iso, det, dwell,
              model_sigma: float = 0.0):
    """(B,P) measurement log-likelihood; identical maths to physics.measurement_loglik."""
    if not HAVE_NUMBA:  # pragma: no cover
        from . import physics as P
        tau = tau_bpn(src, det_xy, rects, mu, nrect, det.height)
        lam = P.expected_counts(src[:, :, None, :], 10.0 ** logA[..., None], det_xy[:, None],
                                iso, det, dwell, tau)
        ll = P.measurement_loglik(counts[:, None, :], lam, model_sigma)
        return (ll * active[:, None, :]).sum(-1)
    f = np.ascontiguousarray
    return _loglik_bp_nb(f(src, dtype=np.float64), f(logA, dtype=np.float64),
                         f(det_xy, dtype=np.float64), f(counts, dtype=np.float64),
                         f(active, dtype=np.float64), f(rects, dtype=np.float64),
                         f(mu, dtype=np.float64), f(nrect, dtype=np.int64), float(det.height),
                         float(iso.mu_air), float(iso.photons_per_decay * det.efficiency),
                         float(det.radius ** 2), float(det.fit_m), float(det.background_cps),
                         float(det.dead_time), float(dwell), float(model_sigma) ** 2)
