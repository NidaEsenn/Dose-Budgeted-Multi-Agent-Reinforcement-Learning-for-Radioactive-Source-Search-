import numpy as np
import pytest

from radsearch import physics as P


@pytest.fixture
def cs():
    return P.Isotope.from_constants("Cs-137")


@pytest.fixture
def co():
    return P.Isotope.from_constants("Co-60")


def test_constants_have_sources():
    c = P.load_constants()
    for name, iso in c["isotopes"].items():
        assert "gamma_constant_source" in iso and "mu_air_source" in iso


def test_gamma_constants_match_section9(cs, co):
    assert co.gamma_constant == pytest.approx(0.351e-3)
    assert cs.gamma_constant == pytest.approx(0.089e-3)


def test_inverse_square(co):
    a = P.dose_rate(np.zeros(2), 1000.0, np.array([1.0, 0]), co, height=0.0, air_attenuation=False)
    b = P.dose_rate(np.zeros(2), 1000.0, np.array([2.0, 0]), co, height=0.0, air_attenuation=False)
    assert a / b == pytest.approx(4.0)
    # 1 TBq Co-60 at 1 m -> 0.351 Gy/h
    assert a == pytest.approx(0.351)


def test_step_dose_is_rate_times_dt():
    assert P.step_dose(3.6, 10.0) == pytest.approx(0.01)


def test_height_removes_singularity(co):
    r = P.dose_rate(np.zeros(2), 1.0, np.zeros(2), co, height=0.3)
    assert np.isfinite(r) and r > 0


@pytest.mark.parametrize("p0,p1,rect,expected", [
    ((0, 0.5), (3, 0.5), (1, 0, 2, 1), 1.0),          # straight through
    ((0, 0), (3, 3), (1, 1, 2, 2), np.sqrt(2)),         # diagonal
    ((0, 5), (3, 5), (1, 0, 2, 1), 0.0),               # miss
    ((1.5, 0.5), (1.5, 0.5), (1, 0, 2, 1), 0.0),       # zero-length
    ((1.5, -1), (1.5, 3), (1, 0, 2, 1), 1.0),          # vertical (dx = 0)
    ((0, 0.5), (1.5, 0.5), (1, 0, 2, 1), 0.5),         # ends inside
    ((1, 0.0), (2, 0.0), (1, 0, 2, 1), 1.0),           # along the edge (boundary)
])
def test_chord_lengths(p0, p1, rect, expected):
    L = P.rect_chord_lengths(np.array(p0, float), np.array(p1, float), np.array([rect], float))
    assert L[0] == pytest.approx(expected, abs=1e-12)


def test_chord_matches_dense_sampling():
    rng = np.random.default_rng(0)
    rects = np.array([[3, 3, 6, 5], [10, 2, 11, 9]], float)
    for _ in range(50):
        p0, p1 = rng.uniform(0, 14, 2), rng.uniform(0, 14, 2)
        exact = P.rect_chord_lengths(p0, p1, rects)
        t = (np.arange(20000) + 0.5) / 20000
        pts = p0 + t[:, None] * (p1 - p0)
        seg = np.linalg.norm(p1 - p0)
        for k, r in enumerate(rects):
            inside = (pts[:, 0] > r[0]) & (pts[:, 0] < r[2]) & (pts[:, 1] > r[1]) & (pts[:, 1] < r[3])
            assert exact[k] == pytest.approx(inside.mean() * seg, abs=2e-3)


def test_wall_attenuation_shadow(cs):
    rects = np.array([[4.0, 0.0, 5.0, 10.0]])
    mu = np.array([cs.mu_material["concrete"]])
    tau = P.wall_optical_depth(np.array([2.0, 5.0]), np.array([7.0, 5.0]), rects, mu, height=0.0)
    assert tau == pytest.approx(cs.mu_material["concrete"] * 1.0)
    tau_clear = P.wall_optical_depth(np.array([2.0, 5.0]), np.array([2.0, 9.0]), rects, mu, height=0.0)
    assert tau_clear == 0.0


def test_slanted_ray_correction(cs):
    rects = np.array([[1.0, -1.0, 2.0, 1.0]])
    mu = np.array([1.0])
    tau = P.wall_optical_depth(np.array([0.0, 0.0]), np.array([3.0, 0.0]), rects, mu, height=4.0)
    assert tau == pytest.approx(1.0 * 5.0 / 3.0)


def test_detector_solid_angle_far_field():
    det = P.Detector.from_constants(fit_m=0.0)
    d = 10.0
    g = P.geometric_efficiency(d, det)
    assert g == pytest.approx(det.radius ** 2 / (4 * d ** 2), rel=1e-3)


def test_expected_counts_scale_and_background(cs):
    det = P.Detector.from_constants()
    lam_bg = P.expected_counts(np.zeros(2), 0.0, np.array([5.0, 0]), cs, det, dwell_s=10.0)
    assert lam_bg == pytest.approx(det.background_cps * 10.0)
    l1 = P.expected_counts(np.zeros(2), 1e12, np.array([5.0, 0]), cs, det, 10.0) - lam_bg
    l2 = P.expected_counts(np.zeros(2), 2e12, np.array([5.0, 0]), cs, det, 10.0) - lam_bg
    assert l2 / l1 == pytest.approx(2.0)


def test_dead_time_saturates(cs):
    det = P.Detector.from_constants(dead_time=1e-4)
    lam = P.expected_counts(np.zeros(2), 1e15, np.array([0.5, 0]), cs, det, 1.0)
    assert lam < 1.0 / 1e-4


def test_broadcasting_shapes(cs):
    det = P.Detector.from_constants()
    src = np.random.rand(7, 100, 1, 2) * 20     # (B, P, 1, 2)
    rob = np.random.rand(7, 1, 4, 2) * 20       # (B, 1, N, 2)
    rects = np.random.rand(7, 1, 1, 3, 4)
    rects[..., 2:] += rects[..., :2]
    mu = np.ones((7, 1, 1, 3))
    tau = P.wall_optical_depth(src, rob, rects, mu, det.height)
    lam = P.expected_counts(src[..., 0, :][..., None, :], 1e12, rob, cs, det, 10.0, tau)
    assert tau.shape == (7, 100, 4) and lam.shape == (7, 100, 4)
