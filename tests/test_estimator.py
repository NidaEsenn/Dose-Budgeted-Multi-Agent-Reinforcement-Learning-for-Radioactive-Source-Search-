import numpy as np
import pytest

from radsearch import physics as P
from radsearch._kernels import loglik_bp, tau_bpn, _tau_bpn_py
from radsearch.estimator import ParticleFilter
from radsearch.world import generate_layout, sample_source


def _geom(B, K, rng):
    rects = rng.uniform(0, 15, (B, K, 4)); rects[..., 2:] = rects[..., :2] + rng.uniform(1, 4, (B, K, 2))
    mu = np.full((B, K), 17.85); mu[:, -1] = 0.0
    return rects, mu, np.full(B, K)


def test_numba_tau_matches_numpy():
    rng = np.random.default_rng(1)
    rects, mu, nrect = _geom(3, 4, rng)
    src, det = rng.uniform(0, 20, (3, 50, 2)), rng.uniform(0, 20, (3, 5, 2))
    np.testing.assert_allclose(tau_bpn(src, det, rects, mu, nrect, 0.3),
                               _tau_bpn_py(src, det, rects, mu, nrect, 0.3), atol=1e-10)


def test_fused_loglik_matches_physics():
    rng = np.random.default_rng(2)
    iso, det = P.Isotope.from_constants("Co-60"), P.Detector.from_constants(dead_time=1e-6)
    rects, mu, nrect = _geom(2, 3, rng)
    src, logA = rng.uniform(0, 20, (2, 40, 2)), rng.uniform(12, 14, (2, 40))
    rob = rng.uniform(0, 20, (2, 4, 2)); counts = rng.integers(0, 1e5, (2, 4)).astype(float)
    act = np.array([[1, 1, 0, 1], [1, 0, 1, 1]], float)
    tau = _tau_bpn_py(src, rob, rects, mu, nrect, det.height)
    lam = P.expected_counts(src[:, :, None], 10 ** logA[..., None], rob[:, None], iso, det, 10.0, tau)
    ref = (P.poisson_loglik(counts[:, None], lam) * act[:, None]).sum(-1)
    np.testing.assert_allclose(loglik_bp(src, logA, rob, counts, act, rects, mu, nrect, iso, det, 10.0),
                               ref, rtol=1e-9)


@pytest.mark.parametrize("variant", ["rpf", "tempered"])
def test_pf_localises_empty_room(variant):
    """AC-2 in miniature: fixed robots around the room, source found within 1 m."""
    iso, det = P.Isotope.from_constants("Cs-137"), P.Detector.from_constants()
    rng = np.random.default_rng(3)
    lay = generate_layout(rng, 4, n_obstacles=0)
    pf = ParticleFilter(1, 2000, iso, det, 10.0, variant=variant)
    pf.set_geometry(np.zeros((1, 0, 4)), np.zeros((1, 0)), np.zeros(1, int))
    pf.reset(0, lay.occ, 1.0, np.random.default_rng(4))
    src = np.array([13.3, 6.7]); A = 10 ** 12.7
    rob = np.array([[[2.5, 2.5], [17.5, 2.5], [2.5, 17.5], [17.5, 17.5]]])
    for t in range(15):
        lam = P.expected_counts(src, A, rob[0], iso, det, 10.0)
        pf.update(rob, rng.poisson(lam)[None].astype(float), np.ones((1, 4)))
    mean, cov = pf.estimate()
    assert np.linalg.norm(mean[0, :2] - src) < 1.0
    assert abs(mean[0, 2] - 12.7) < 0.2


def test_pf_ignores_inactive_robots():
    iso, det = P.Isotope.from_constants("Cs-137"), P.Detector.from_constants()
    pf = ParticleFilter(1, 500, iso, det, 10.0)
    pf.set_geometry(np.zeros((1, 0, 4)), np.zeros((1, 0)), np.zeros(1, int))
    pf.reset(0, np.zeros((20, 20), bool), 1.0, np.random.default_rng(0))
    x0 = pf.x.copy()
    pf.update(np.ones((1, 2, 2)), np.array([[1e6, 5.0]]), np.zeros((1, 2)))
    np.testing.assert_array_equal(pf.x, x0)


def test_pf_reproducible():
    iso, det = P.Isotope.from_constants("Cs-137"), P.Detector.from_constants()
    out = []
    for _ in range(2):
        pf = ParticleFilter(1, 500, iso, det, 10.0)
        pf.set_geometry(np.zeros((1, 0, 4)), np.zeros((1, 0)), np.zeros(1, int))
        pf.reset(0, np.zeros((20, 20), bool), 1.0, np.random.default_rng(7))
        pf.update(np.array([[[3.5, 3.5]]]), np.array([[2000.0]]), np.ones((1, 1)))
        out.append(pf.estimate()[0])
    np.testing.assert_array_equal(out[0], out[1])


def test_fused_lognormal_loglik_matches_physics():
    rng = np.random.default_rng(5)
    iso, det = P.Isotope.from_constants("Cs-137"), P.Detector.from_constants()
    rects, mu, nrect = _geom(2, 2, rng)
    src, logA = rng.uniform(0, 20, (2, 30, 2)), rng.uniform(12, 14, (2, 30))
    rob = rng.uniform(0, 20, (2, 3, 2)); counts = rng.integers(0, 1e5, (2, 3)).astype(float)
    act = np.ones((2, 3))
    tau = _tau_bpn_py(src, rob, rects, mu, nrect, det.height)
    lam = P.expected_counts(src[:, :, None], 10 ** logA[..., None], rob[:, None], iso, det, 10.0, tau)
    ref = P.measurement_loglik(counts[:, None], lam, 0.2).sum(-1)
    np.testing.assert_allclose(loglik_bp(src, logA, rob, counts, act, rects, mu, nrect, iso, det, 10.0, 0.2),
                               ref, rtol=1e-9)


def test_model_error_is_mean_preserving():
    rng = np.random.default_rng(0)
    lam = np.full(200000, 1e4)
    assert P.apply_model_error(rng, lam, 0.3).mean() == pytest.approx(1e4, rel=0.01)
