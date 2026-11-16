"""Equation panels for the backup slides (formula + plain-language meaning per row).

    python scripts/make_figures_math.py
      -> docs/figures/math_filter.png, math_greedy.png, math_mappo.png, math_lagrangian.png

Every formula mirrors the code: radsearch/estimator.py, radsearch/physics.py,
radsearch/baselines/policies.py, radsearch/shield.py, radsearch/algos/mappo.py.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

INK, MUTED, BLUE, ORANGE, LIGHT = "#14213D", "#4A5568", "#2F6FB3", "#E0871F", "#F3F4F6"
plt.rcParams.update({"font.family": "Inter", "mathtext.fontset": "cm"})


def panel(rows, path, accent=BLUE, fw=15.0, row_h=1.5, split=0.53):
    """rows: list of (label, [formula lines], explanation)."""
    H = row_h * len(rows) + 0.15
    fig = plt.figure(figsize=(fw, H), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, fw); ax.set_ylim(0, H)
    for k, (label, formulas, expl) in enumerate(rows):
        y0 = H - (k + 1) * row_h
        ax.add_patch(FancyBboxPatch((0.08, y0 + 0.08), fw - 0.16, row_h - 0.16,
                                    boxstyle="round,pad=0,rounding_size=0.12", fc=LIGHT, ec="none"))
        ax.add_patch(Circle((0.5, y0 + row_h / 2), 0.25, fc=accent, ec="none"))
        ax.text(0.5, y0 + row_h / 2, str(k + 1), ha="center", va="center", color="white", fontsize=15, fontweight="bold")
        ax.text(0.95, y0 + row_h - 0.24, label, ha="left", va="center", fontsize=13, fontweight="bold", color=accent)
        n = len(formulas)
        for m, f in enumerate(formulas):
            yy = y0 + row_h / 2 - 0.16 - (m - (n - 1) / 2) * 0.46
            ax.text(0.95, yy, f, ha="left", va="center", fontsize=17 if n == 1 else 15.5, color=INK)
        ax.text(fw * split + 0.35, y0 + row_h / 2, expl, ha="left", va="center", fontsize=12.5, color=INK,
                linespacing=1.35, wrap=False)
        ax.plot([fw * split + 0.1] * 2, [y0 + 0.22, y0 + row_h - 0.22], color="#D1D5DB", lw=1.2)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


panel([
    ("Belief = 2,000 weighted guesses",
     [r"$p(\theta \mid k_{1:t}) \approx \sum_{j=1}^{2000} w_j\, \delta(\theta - \theta_j)$, $\theta = (x,\, y,\, \log_{10} A)$"],
     "Each particle is one possible source: position and strength.\nAt the start: spread over the whole room and 10–100 TBq."),
    ("Expected count for robot i",
     [r"$\lambda_i(\theta) = t\, \left[\, b + A\, n_\gamma\, \varepsilon\, G(d_i)\, e^{-\mu d_i}\, e^{-\sum_k \mu_k \ell_k} \right]$"],
     "What robot i should count in 10 s if guess θ were true:\nG ≈ area / 4πd² (inverse square), air and wall attenuation."),
    ("Bayes update (tempered)",
     [r"$w_j \;\leftarrow\; w_j \prod_i \mathcal{L}(k_i \mid \lambda_i(\theta_j))^{\alpha}$",
      r"$\log(k+\frac{1}{2}) \sim \mathcal{N}(\log(\lambda+\frac{1}{2}),\; \sigma^2 + \frac{1}{\lambda+1/2}),\;\; \sigma = 0.3$"],
     "Guesses that explain the counts gain weight.\nσ adds the ~30% model error. Done in ≤ 3 stages (Σα = 1)\nso the effective sample size 1/Σw² stays ≥ 1,000."),
    ("Resample, jitter, declare",
     [r"$\theta_j \sim \mathrm{Cat}(w), \quad \theta_j \leftarrow \theta_j + \mathcal{N}(0,\, h^2 \hat\Sigma)$",
      r"declare $\hat\theta = \sum_j w_j \theta_j$  when  $\sqrt{\lambda_{\max}(\hat\Sigma_{xy})} < 0.3$ m"],
     "Copy likely guesses, add a small jitter to keep them diverse.\nWhen the position spread is below 0.3 m, the team names\nthe weighted mean. Success = within 1 m."),
], "docs/figures/math_filter.png", accent=BLUE)

panel([
    ("Information gain of a move",
     [r"$I(a) = \frac{1}{2} \log\!\left(1 + \dfrac{\mathrm{Var}_j[\lambda(c_a;\, \theta_j)]}{\mathbb{E}_j[\lambda(c_a;\, \theta_j)]}\right)$"],
     "If the sampled guesses (128) disagree about the count\nin the next cell c_a, a reading there teaches a lot\n(Gaussian approx. of the Poisson mutual information)."),
    ("Score: information vs dose",
     [r"$\mathrm{score}(a) = I(a) \;-\; \beta\, \dfrac{\mathbb{E}_j[D_{\mathrm{step}}(c_a;\, \theta_j)]}{B - D_{\mathrm{used}}}$"],
     "Trade what we learn against the expected dose,\nscaled by the budget that is left (reference β = 1)."),
    ("Team: choose in turn",
     [r"$\mathrm{score}_i(a) \leftarrow \mathrm{score}_i(a) - c\, |\mathrm{score}_i(a)|$  if  $c_a$  is taken",
      r"$a_i = \arg\max_a \mathrm{score}_i(a)$"],
     "Robots pick one after another; a cell a teammate already\nchose is penalised (c = 0.5), so the team spreads out.\nHeadroom test: this term matters most (no penalty: ~ −8 pts)."),
    ("Safety layer on top",
     [r"$D_{\mathrm{used}} + Q_{0.97}\{\, D_{\mathrm{step}}(c_a;\theta_j) + D_{\mathrm{exit}}(c_a;\theta_j) \,\}_{j=1}^{32} \;\leq\; B$"],
     "Checked for the chosen move with 32 guesses. D_exit = dose\nof the lowest-dose shortest path to the door.\nIf it fails, the robot withdraws (always allowed)."),
], "docs/figures/math_greedy.png", accent=INK)

panel([
    ("Train together, act alone (CTDE)",
     [r"actor $\pi_\phi(a_i \mid o_i)$, shared by all robots",
      r"critic $V_\psi(s,\, o_i)$, training only"],
     "One network (2 × 128) for every robot, on its own view:\nposition, counts, budget left, team estimate, teammates.\nThe critic also sees the true source, only in training."),
    ("Shared team reward",
     [r"$r_t = \gamma\, \Phi(s_{t+1}) - \Phi(s_t) \;-\; \mathbb{1}[\mathrm{wrong\ declaration}], \quad \Phi = -\,\mathrm{error}/5$"],
     "Reward for shrinking the error of the team's estimate.\nPotential shaping: it guides learning without changing\nwhich policy is best. A withdrawn robot still shares it."),
    ("Advantage (GAE)",
     [r"$\hat A_t = \sum_{l \geq 0} (\gamma \lambda)^l\, \delta_{t+l}, \quad \delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$"],
     "How much better than expected an action turned out.\nγ = 0.99, λ = 0.95."),
    ("PPO update",
     [r"$L(\phi) = \mathbb{E}[\min(\rho_t \hat A_t,\; \mathrm{clip}(\rho_t,\, 1 \pm 0.2)\, \hat A_t)], \quad \rho_t = \dfrac{\pi_\phi(a_t \mid o_t)}{\pi_{\mathrm{old}}(a_t \mid o_t)}$"],
     "Make good actions more likely, but limit each step\n(clip 0.2). Actions the safety layer blocks are masked\nout before sampling."),
], "docs/figures/math_mappo.png", accent=BLUE, split=0.56)

panel([
    ("Constrained goal",
     [r"$\max_\pi \; J_r(\pi) \quad \mathrm{s.t.} \quad J_c^i(\pi) = P(\mathrm{robot}\ i\ \mathrm{goes\ over\ budget}) \leq d = \frac{0.05}{N}$"],
     "High team reward, while at most 5% of missions have\nany robot over budget (union bound: 5% / N per robot)."),
    ("Cost signal",
     [r"$c_t^i = \mathbb{1}[\, D^i\ \mathrm{crosses}\ B\ \mathrm{at}\ t \,] + \kappa\, D^i_{\mathrm{step}}, \quad \kappa = 0.01$"],
     "Cost 1 at the step a robot goes over its budget,\nplus a tiny per-dose term that gives an earlier signal."),
    ("Price update (dual ascent)",
     [r"$\lambda_i \;\leftarrow\; \max(0,\; \lambda_i + \eta\, (\hat J_c^i - d))$"],
     "The price rises while failures are above the target\nand falls when they are below."),
    ("Combined advantage for PPO",
     [r"$\hat A = \dfrac{\hat A_r - \lambda\, \hat A_c}{1 + \lambda}$"],
     "Risky actions lose value as the price grows.\nBefore the withdraw action: λ grew until robots stayed\n~13 m away (10% success). Now: 79.6% success, 4.3% fail."),
], "docs/figures/math_lagrangian.png", accent=ORANGE, split=0.56)
print("ok")
