# -*- coding: utf-8 -*-
"""
StatPoisk / 2x2StatSearch — single-file program
Exact tests for 2x2 contingency tables.

Android: Pydroid 3 or Termux
PC:      python statpoisk.py

Requires: numpy, scipy
"""

import math
from math import gcd

import numpy as np
from scipy.stats import fisher_exact, binom, chi2_contingency, boschloo_exact, chi2


# ============================================================
# РАСЧЁТЫ
# ============================================================

def observed_probability(a, b, c, d):
    """Вероятность наблюдаемой таблицы (гипергеометрическое распределение)."""
    n = a + b + c + d
    if n == 0:
        return float("nan")
    try:
        log_p = (
            math.lgamma(a + b + 1) - math.lgamma(a + 1) - math.lgamma(b + 1)
            + math.lgamma(c + d + 1) - math.lgamma(c + 1) - math.lgamma(d + 1)
            + math.lgamma(a + c + 1) + math.lgamma(b + d + 1)
            - math.lgamma(n + 1)
        )
        return math.exp(log_p)
    except Exception:
        return float("nan")


def fisher_mid_p(a, b, c, d, alternative):
    """Fisher mid-p = exact p-value − 0.5 × P(наблюдаемой таблицы)."""
    table = np.array([[a, b], [c, d]])
    _, p_exact = fisher_exact(table, alternative=alternative)
    p_observed = observed_probability(a, b, c, d)
    mid_p = p_exact - 0.5 * p_observed
    return max(0.0, min(1.0, mid_p)), p_observed


def _fmt_or(x):
    """Форматирование OR: 0 / ∞ / число."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "не определено"
    if isinstance(x, float) and math.isinf(x):
        return "∞" if x > 0 else "0"
    return f"{x:.8f}"


def _fmt_num(x, digits=8):
    """Форматирование числа; nan → «не определено»."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "не определено"
    if isinstance(x, float) and math.isinf(x):
        return "∞" if x > 0 else "−∞"
    return f"{x:.{digits}f}"


def odds_ratio_ci(a, b, c, d):
    """
    Отношение шансов и 95% ДИ (метод Woolf / logit).

    Возвращает:
      sample_or  — выборочный OR = ad/bc (0 / ∞ при нулях в ячейках)
      woolf_or   — OR после поправки Халдейна–Анскомба (+0.5), если она нужна
      ci_low, ci_high — 95% ДИ Woolf на log-шкале
      correction — True, если применена поправка +0.5
      note       — пояснение

    Рекомендация Ruxton & Neuhäuser (2013): Woolf + Haldane–Anscombe —
    практичный и хорошо калиброванный метод для 2×2.
    """
    aa0, bb0, cc0, dd0 = float(a), float(b), float(c), float(d)

    # --- Выборочный (сырой) OR ---
    if bb0 == 0 and aa0 == 0:
        sample_or = float("nan")  # 0/0
    elif bb0 == 0 or cc0 == 0:
        # ad/bc → ∞, если числитель > 0; иначе 0/0-подобная неопределённость
        if aa0 * dd0 > 0 and (bb0 == 0 or cc0 == 0):
            sample_or = float("inf")
        elif aa0 * dd0 == 0 and (bb0 == 0 or cc0 == 0):
            sample_or = float("nan")
        else:
            sample_or = 0.0
    elif aa0 * dd0 == 0:
        sample_or = 0.0
    else:
        sample_or = (aa0 * dd0) / (bb0 * cc0)

    # --- Woolf OR + ДИ (Haldane–Anscombe при любой нулевой ячейке) ---
    correction = min(aa0, bb0, cc0, dd0) == 0
    aa, bb, cc, dd = aa0, bb0, cc0, dd0
    if correction:
        aa += 0.5
        bb += 0.5
        cc += 0.5
        dd += 0.5

    # После +0.5 знаменатель всегда > 0
    woolf_or = (aa * dd) / (bb * cc)
    log_or = math.log(woolf_or)
    se = math.sqrt(1.0 / aa + 1.0 / bb + 1.0 / cc + 1.0 / dd)
    z = 1.959963984540054  # norm.ppf(0.975)
    ci_low = math.exp(log_or - z * se)
    ci_high = math.exp(log_or + z * se)

    if correction:
        note = (
            "Поправка Халдейна–Анскомба (+0.5 ко всем ячейкам) применена "
            "из-за нулевых частот; ДИ — метод Woolf (logit). / "
            "Haldane–Anscombe correction (+0.5 to all cells) applied due to zero counts; "
            "CI — Woolf (logit) method."
        )
    else:
        note = (
            "ДИ — метод Woolf (logit) без поправки непрерывности. / "
            "CI — Woolf (logit) method without continuity correction."
        )

    return {
        "sample_or": sample_or,
        "woolf_or": woolf_or,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "correction": correction,
        "note": note,
    }


def chi2_tests(a, b, c, d):
    """χ² Пирсона и χ² с поправкой Йейтса (для 2×2)."""
    table = np.array([[a, b], [c, d]], dtype=float)
    # Вырожденная таблица (нулевая строка/столбец) — χ² не определён
    if (a + b) == 0 or (c + d) == 0 or (a + c) == 0 or (b + d) == 0:
        return {
            "chi2": float("nan"),
            "chi2_p": float("nan"),
            "yates": float("nan"),
            "yates_p": float("nan"),
            "expected": None,
        }
    try:
        chi2_stat, p_chi2, dof, expected = chi2_contingency(table, correction=False)
        chi2_yates, p_yates, _, _ = chi2_contingency(table, correction=True)
        return {
            "chi2": float(chi2_stat),
            "chi2_p": float(p_chi2),
            "yates": float(chi2_yates),
            "yates_p": float(p_yates),
            "expected": expected,
        }
    except ValueError:
        return {
            "chi2": float("nan"),
            "chi2_p": float("nan"),
            "yates": float("nan"),
            "yates_p": float("nan"),
            "expected": None,
        }


def mcnemar_tests(a, b, c, d):
    """
    Критерий Макнемара для парных данных.
    Таблица: a=оба+, b=только1, c=только2, d=оба−.
    Дискордантные пары: b и c.
    exact — точный биномиальный; asymptotic — χ² с/без поправки.
    """
    n_discordant = b + c
    if n_discordant == 0:
        return {
            "exact_stat": 0.0,
            "exact_p": 1.0,
            "chi2_stat": 0.0,
            "chi2_p": 1.0,
            "chi2_corr_stat": 0.0,
            "chi2_corr_p": 1.0,
            "b": b,
            "c": c,
            "n_discordant": 0,
        }

    # Точный тест (биномиальный, двусторонний)
    # statistic = min(b, c); p = 2 * BinomCDF(min, n, 0.5)
    k = min(b, c)
    p_exact = min(1.0, 2.0 * binom.cdf(k, n_discordant, 0.5))

    # Асимптотический без поправки: (b - c)² / (b + c)
    chi2_stat = (b - c) ** 2 / n_discordant
    p_chi2 = 1.0 - chi2.cdf(chi2_stat, 1)

    # С поправкой непрерывности: (|b - c| - 1)² / (b + c)
    chi2_corr = (abs(b - c) - 1) ** 2 / n_discordant
    if chi2_corr < 0:
        chi2_corr = 0.0
    p_corr = 1.0 - chi2.cdf(chi2_corr, 1)

    return {
        "exact_stat": float(k),
        "exact_p": float(p_exact),
        "chi2_stat": float(chi2_stat),
        "chi2_p": float(p_chi2),
        "chi2_corr_stat": float(chi2_corr),
        "chi2_corr_p": float(p_corr),
        "b": b,
        "c": c,
        "n_discordant": n_discordant,
    }


def boschloo_test(a, b, c, d, alternative="two-sided"):
    """Точный критерий Бошлу (Boschloo) — равномерно более мощный, чем Fisher."""
    # Вырожденные маргиналы
    if (a + b) == 0 or (c + d) == 0 or (a + c) == 0 or (b + d) == 0:
        return {"statistic": float("nan"), "pvalue": float("nan")}
    table = np.array([[a, b], [c, d]])
    try:
        res = boschloo_exact(table, alternative=alternative)
        return {
            "statistic": float(res.statistic),
            "pvalue": float(res.pvalue),
        }
    except Exception:
        return {
            "statistic": float("nan"),
            "pvalue": float("nan"),
        }


def barnard_exact_precise(a, b, c, d, alternative="two-sided",
                          grid_points=1001, groups="rows"):
    """
    Точный критерий Барнарда (векторизованный).
    Соответствует R Barnard (dp=0.001) и scipy.stats.barnard_exact (pooled=True).
    """
    if groups == "columns":
        n1 = a + c
        n2 = b + d
        p1_obs = a / n1 if n1 > 0 else 0.0
        p2_obs = b / n2 if n2 > 0 else 0.0
        p_pooled_obs = (a + b) / (n1 + n2) if (n1 + n2) > 0 else 0.0
    else:
        n1 = a + b
        n2 = c + d
        p1_obs = a / n1 if n1 > 0 else 0.0
        p2_obs = c / n2 if n2 > 0 else 0.0
        p_pooled_obs = (a + c) / (n1 + n2) if (n1 + n2) > 0 else 0.0

    diff_obs = p1_obs - p2_obs

    if p_pooled_obs == 0 or p_pooled_obs == 1:
        z_obs = float("inf") if diff_obs != 0 else 0.0
    else:
        se = math.sqrt(p_pooled_obs * (1 - p_pooled_obs) * (1 / n1 + 1 / n2))
        z_obs = (diff_obs / se) if se > 0 else (float("inf") if diff_obs != 0 else 0.0)

    if z_obs == 0.0:
        return {
            "pvalue": 1.0,
            "statistic": z_obs,
            "pi_max": 0.0,
            "groups": groups,
            "n1": n1,
            "n2": n2,
        }

    x1_vals = np.arange(n1 + 1)
    x2_vals = np.arange(n2 + 1)
    pi_grid = np.linspace(0, 1, grid_points)

    pmf1 = np.array([binom.pmf(x1_vals, n1, pi) for pi in pi_grid])
    pmf2 = np.array([binom.pmf(x2_vals, n2, pi) for pi in pi_grid])

    z_table = np.zeros((n1 + 1, n2 + 1))
    for x1 in range(n1 + 1):
        for x2 in range(n2 + 1):
            p1 = x1 / n1 if n1 > 0 else 0.0
            p2 = x2 / n2 if n2 > 0 else 0.0
            diff = p1 - p2
            total = n1 + n2
            p_pooled = (x1 + x2) / total if total > 0 else 0.0
            if p_pooled == 0 or p_pooled == 1:
                z = float("inf") if diff != 0 else 0.0
            else:
                se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))
                z = (diff / se) if se > 0 else (float("inf") if diff != 0 else 0.0)
            z_table[x1, x2] = z

    if alternative == "two-sided":
        more_extreme = np.abs(z_table) >= np.abs(z_obs)
    elif alternative == "less":
        more_extreme = z_table <= z_obs
    else:
        more_extreme = z_table >= z_obs

    p_values = np.zeros(grid_points)
    for i in range(len(pi_grid)):
        joint = pmf1[i, :, None] * pmf2[i, None, :]
        p_values[i] = np.sum(joint[more_extreme])

    max_idx = int(np.argmax(p_values))
    return {
        "pvalue": float(p_values[max_idx]),
        "statistic": z_obs,
        "pi_max": float(pi_grid[max_idx]),
        "groups": groups,
        "n1": n1,
        "n2": n2,
    }


def detect_orientation(a, b, c, d):
    """Автоопределение ориентации групп для Барнарда."""
    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d

    rows_equal = row1 == row2
    cols_equal = col1 == col2

    if rows_equal and not cols_equal:
        return "rows", f"Итоги строк равны ({row1}={row2}) — сбалансированный дизайн / Row totals equal ({row1}={row2}) — balanced design"
    if cols_equal and not rows_equal:
        return "columns", f"Итоги столбцов равны ({col1}={col2}) — сбалансированный дизайн / Column totals equal ({col1}={col2}) — balanced design"
    if rows_equal and cols_equal:
        return "columns", "Оба измерения сбалансированы — стандарт scipy/R/SAS (столбцы) / Both margins balanced — scipy/R/SAS default (columns)"

    row_score = col_score = 0
    reasons_r, reasons_c = [], []

    max_r = max(row1, row2)
    max_c = max(col1, col2)
    cv_r = abs(row1 - row2) / max_r if max_r > 0 else 1.0
    cv_c = abs(col1 - col2) / max_c if max_c > 0 else 1.0

    if cv_r < cv_c:
        row_score += 2
        reasons_r.append(f"строки сбалансированы (отн. разница={cv_r:.3f} < {cv_c:.3f}) / rows more balanced (rel.diff={cv_r:.3f} < {cv_c:.3f})")
    elif cv_c < cv_r:
        col_score += 2
        reasons_c.append(f"столбцы сбалансированы (отн. разница={cv_c:.3f} < {cv_r:.3f}) / columns more balanced (rel.diff={cv_c:.3f} < {cv_r:.3f})")

    rows_round = (row1 % 5 == 0) + (row2 % 5 == 0)
    cols_round = (col1 % 5 == 0) + (col2 % 5 == 0)
    if rows_round > cols_round:
        row_score += 1
        reasons_r.append(f"круглые итоги строк ({row1}, {row2})")
    elif cols_round > rows_round:
        col_score += 1
        reasons_c.append(f"круглые итоги столбцов ({col1}, {col2})")

    def simple_ratio(n1, n2):
        if n1 == 0 or n2 == 0:
            return False
        g = gcd(n1, n2)
        r1, r2 = n1 // g, n2 // g
        return (r1, r2) in {
            (1, 1), (1, 2), (2, 1), (1, 3), (3, 1),
            (2, 3), (3, 2), (1, 4), (4, 1), (3, 4), (4, 3),
        }

    if simple_ratio(row1, row2) and not simple_ratio(col1, col2):
        row_score += 1
        reasons_r.append(f"простое соотношение строк ({row1}:{row2})")
    elif simple_ratio(col1, col2) and not simple_ratio(row1, row2):
        col_score += 1
        reasons_c.append(f"простое соотношение столбцов ({col1}:{col2})")

    if row_score > col_score:
        return "rows", "; ".join(reasons_r)
    if col_score > row_score:
        return "columns", "; ".join(reasons_c)
    return "columns", "однозначно не определено — стандарт scipy/R/SAS (столбцы)"




def _enrich_recommendation_en(rec):
    """Add primary_en, reason_en, notes_en for bilingual UI."""
    primary_map = {
        "Барнард": "Barnard",
        "Бошлу": "Boschloo",
        "χ² Пирсона": "Pearson χ²",
        "Йейтс или Барнард": "Yates or Barnard",
        "Макнемар": "McNemar",
        "Макнемар (точный)": "McNemar (exact)",
        "недостаточно данных": "insufficient data",
        "Барнард (если группы независимы)": "Barnard (if groups are independent)",
        "χ² Пирсона (если группы независимы)": "Pearson χ² (if groups are independent)",
    }
    primary = rec.get("primary") or ""
    if primary in primary_map:
        rec["primary_en"] = primary_map[primary]
    else:
        # e.g. "Барнард (если группы независимы)"
        rec["primary_en"] = primary
        for k, v in sorted(primary_map.items(), key=lambda kv: -len(kv[0])):
            if k in primary:
                rec["primary_en"] = primary.replace(k, v)
                break

    n = rec.get("n")
    min_exp = rec.get("min_expected")
    design = rec.get("design", "independent")
    n_disc = rec.get("n_discordant")
    has_zero = rec.get("has_zero")
    any_lt5 = rec.get("any_exp_lt5")

    # Build reason_en from structured fields when possible
    pe = rec["primary_en"]
    if primary.startswith("недостаточно"):
        reason_en = "Zero row or column — association tests are not applicable."
    elif design == "paired":
        if n_disc == 0:
            reason_en = (
                "Paired design selected, but there are no discordant pairs (b + c = 0). "
                "McNemar formally gives p = 1; check table coding (b and c are discordant outcomes)."
            )
        elif n_disc is not None and n_disc < 25:
            reason_en = (
                f"For paired data, McNemar's exact (binomial) test is recommended: "
                f"discordant pairs b + c = {n_disc}. Asymptotic McNemar χ² is less reliable with few pairs."
            )
        else:
            reason_en = (
                f"For paired data, McNemar's test is recommended "
                f"(discordant pairs = {n_disc}). Report both exact and asymptotic variants if useful."
            )
    elif design == "unknown":
        # reason already mixed; provide independent-case English + note
        if pe.startswith("Barnard"):
            reason_en = (
                f"Design not specified. If groups are independent: with n = {n}, min expected ≈ "
                f"{min_exp:.2f}, Barnard's exact test is preferred over asymptotic χ². "
                "If observations are paired, switch design to Paired and use McNemar."
            ) if min_exp == min_exp else (
                f"Design not specified. If independent, Barnard is preferred at n = {n}. "
                "If paired, choose Paired design for McNemar."
            )
        else:
            reason_en = (
                f"Design not specified. If independent: n = {n}, min E ≈ {min_exp:.2f} — "
                f"{pe} is appropriate. If paired, select Paired and use McNemar."
            ) if min_exp == min_exp else (
                f"Design not specified. If independent, {pe} is appropriate at n = {n}."
            )
    else:
        # independent
        if pe == "Barnard" and (n is not None and n < 20 or has_zero or (min_exp == min_exp and min_exp < 1)):
            reason_en = (
                f"At n = {n} (small sample"
                + (f", min E ≈ {min_exp:.2f}" if min_exp == min_exp else "")
                + ") Barnard's exact test is recommended. Asymptotic χ² is unreliable at this size."
            )
        elif pe == "Barnard" and n is not None and n < 40:
            reason_en = (
                f"At n = {n} (moderate sample, min E ≈ {min_exp:.2f}) 2x2StatSearch recommends "
                "Barnard's exact test. Even when min E ≥ 5, exact tests are more reliable for small n."
            ) if min_exp == min_exp else (
                f"At n = {n}, Barnard's exact test is recommended."
            )
        elif pe == "Barnard":
            reason_en = (
                f"At n = {n}, some expected counts are < 5 (min E ≈ {min_exp:.2f}). "
                "Barnard (or Boschloo) is recommended; Pearson χ² may distort the p-value."
            ) if min_exp == min_exp else (
                f"At n = {n}, Barnard's exact test is recommended."
            )
        elif pe.startswith("Pearson"):
            if n is not None and n < 100:
                reason_en = (
                    f"At n = {n} and min E ≈ {min_exp:.2f} ≥ 5, Pearson χ² is acceptable. "
                    "Consider reporting Barnard or Boschloo as a sensitivity check."
                ) if min_exp == min_exp else (
                    f"At n = {n}, Pearson χ² is acceptable; exact tests remain valid as sensitivity analysis."
                )
            else:
                reason_en = (
                    f"At n = {n} and min E ≈ {min_exp:.2f} ≥ 5, Pearson χ² is the primary test. "
                    "Fisher / Barnard / Boschloo remain valid for robustness checks."
                ) if min_exp == min_exp else (
                    f"At n = {n}, Pearson χ² is appropriate."
                )
        else:
            reason_en = rec.get("reason") or ""

    rec["reason_en"] = reason_en

    notes_en = []
    if design == "independent":
        notes_en.append(
            "McNemar is not recommended as primary: it is only for paired data "
            "(before/after, matched pairs). Independent-groups mode is selected."
        )
    elif design == "unknown":
        notes_en.append(
            "Clarify design: independent groups or paired observations? "
            "That determines whether McNemar is appropriate."
        )
        notes_en.append(
            "If data are paired, switch design to Paired — 2x2StatSearch will recommend McNemar."
        )
    elif design == "paired":
        notes_en.append(
            "Fisher / Barnard / Boschloo / Pearson χ² are shown for reference, "
            "but with a paired design the main conclusion should follow McNemar."
        )

    if pe == "Barnard":
        notes_en.append(
            "Boschloo is a close alternative to Barnard; both are preferable to Fisher "
            "under an unconditional design (two independent groups)."
        )
        notes_en.append(
            "Fisher is appropriate when both margins are fixed by design (conditional test)."
        )
        if any_lt5:
            notes_en.append("When min E < 5, do not use Pearson χ² as the sole conclusion.")
        if has_zero:
            notes_en.append("The table contains zeros — another reason to prefer an exact test.")
        if n is not None and 20 <= n < 40 and not any_lt5:
            notes_en.append(
                "Boschloo and Fisher (mid-p) are also acceptable. "
                "χ² / Yates only as supplements, not as the sole result."
            )
            notes_en.append(
                "Formally min E ≥ 5, but at n < 50 2x2StatSearch still prefers an exact test."
            )
    if pe.startswith("Pearson") and n is not None and n < 100:
        notes_en.append(
            "Sample size is still moderate (n < 100) — reporting an exact p next to χ² strengthens the result."
        )
    if pe.startswith("Pearson") and n is not None and n >= 100:
        notes_en.append(
            "On large n, χ² and exact p-values are usually close; a large discrepancy warrants checking the table."
        )
    if design != "paired" and (rec.get("notes") and any("Сбалансированные" in str(x) for x in rec.get("notes") or [])):
        notes_en.append(
            "Balanced margins: for Barnard, orientation by equal totals is convenient (Auto mode accounts for this)."
        )

    rec["notes_en"] = notes_en
    avoid = rec.get("avoid") or []
    avoid_map = {
        "χ² Пирсона": "Pearson χ²",
        "χ² Пирсона без поправки как единственный вывод": "uncorrected Pearson χ² as the sole conclusion",
        "χ² без поправки (асимптотика ненадёжна)": "uncorrected χ² (asymptotics unreliable)",
        "Йейтс": "Yates",
        "χ² Пирсона как тест независимых групп": "Pearson χ² as a test for independent groups",
        "Барнард как основной вывод": "Barnard as the primary conclusion",
    }
    rec["avoid_en"] = [avoid_map.get(a, a) for a in avoid]
    return rec



def recommend_test(a, b, c, d, expected=None, design="independent"):
    """
    Рекомендация критерия по характеристикам таблицы 2×2.
    Возвращает dict: primary, reason, level, notes (list), avoid (list).
    """
    n = a + b + c + d
    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d
    cells = [a, b, c, d]
    has_zero = min(cells) == 0
    notes = []
    avoid = []
    design = (design or "independent").lower()
    if design not in ("independent", "paired", "unknown"):
        design = "independent"

    # Expected frequencies under independence
    if expected is None and n > 0 and row1 > 0 and row2 > 0 and col1 > 0 and col2 > 0:
        expected = [
            row1 * col1 / n, row1 * col2 / n,
            row2 * col1 / n, row2 * col2 / n,
        ]
    if expected is None:
        exp_list = []
    else:
        try:
            import numpy as _np
            exp_list = [float(x) for x in _np.asarray(expected).ravel()]
        except Exception:
            exp_list = [float(x) for x in expected]
    min_exp = min(exp_list) if exp_list else float("nan")
    any_exp_lt5 = any(e < 5 for e in exp_list) if exp_list else True
    any_exp_lt1 = any(e < 1 for e in exp_list) if exp_list else has_zero

    balanced_cols = col1 == col2 and col1 > 0
    balanced_rows = row1 == row2 and row1 > 0

    # --- Degenerate ---
    if n == 0 or row1 == 0 or row2 == 0 or col1 == 0 or col2 == 0:
        return {
            "primary": "недостаточно данных",
            "reason": "Нулевая строка или столбец — критерии ассоциации не применимы.",
            "level": "error",
            "notes": notes,
            "avoid": ["χ² Пирсона", "Йейтс"],
            "min_expected": min_exp if min_exp == min_exp else None,
            "n": n,
            "design": design,
        }

    # --- Paired design → McNemar ---
    if design == "paired":
        n_disc = b + c
        if n_disc == 0:
            primary = "Макнемар"
            reason = (
                "Указаны парные (зависимые) наблюдения, но дискордантных пар нет (b + c = 0). "
                "Макнемар формально даёт p = 1; проверьте разметку таблицы "
                "(b и c — несогласованные исходы)."
            )
            level = "caution"
        elif n_disc < 25:
            primary = "Макнемар (точный)"
            reason = (
                f"Для парных данных рекомендуется критерий Макнемара (точный биномиальный): "
                f"дискордантных пар b + c = {n_disc}. "
                "Асимптотический χ² Макнемара при малом числе пар менее надёжен."
            )
            level = "recommend"
        else:
            primary = "Макнемар"
            reason = (
                f"Для парных данных рекомендуется критерий Макнемара "
                f"(дискордантных пар = {n_disc}). "
                "Можно привести точный и асимптотический варианты."
            )
            level = "recommend"
        notes.append(
            "Фишер / Барнард / Бошлу / χ² Пирсона рассчитаны для справки, "
            "но при парном дизайне основной вывод — по Макнемару."
        )
        avoid.extend(["χ² Пирсона как тест независимых групп", "Барнард как основной вывод"])
        return {
            "primary": primary,
            "reason": reason,
            "level": level,
            "notes": notes,
            "avoid": avoid,
            "min_expected": float(min_exp) if min_exp == min_exp else None,
            "n": n,
            "has_zero": has_zero,
            "any_exp_lt5": bool(any_exp_lt5),
            "design": design,
            "n_discordant": n_disc,
        }

    # --- Unknown design: ask + dual advice ---
    if design == "unknown":
        notes.append(
            "Уточните дизайн: независимые группы или парные наблюдения? "
            "От этого зависит, нужен ли Макнемар."
        )

    # --- Independent (default): rules by n and expected frequencies ---
    notes.append(
        "Макнемар не рекомендован как основной: он только для парных данных "
        "(до/после, matched pairs). Сейчас выбран режим независимых групп."
        if design == "independent"
        else "Если данные парные — переключите дизайн на «Парные», и СтатПоиск порекомендует Макнемар."
    )

    # Cochran-style + sample-size tiers for StatPoisk
    # n < 20  → only exact
    # 20–39   → prefer exact (even if min E ≥ 5)
    # 40–99   → exact if min E < 5, else χ² with note
    # n ≥ 100 and min E ≥ 5 → χ² primary

    if any_exp_lt1 or has_zero or n < 20:
        primary = "Барнард"
        reason = (
            f"При n = {n} (малая выборка"
            + (f", min E ≈ {min_exp:.2f}" if min_exp == min_exp else "")
            + ") рекомендуется точный критерий Барнарда. "
            "Асимптотический χ² при таком объёме ненадёжен."
        )
        level = "recommend"
        notes.append(
            "Бошлу — близкая альтернатива; Фишер — если оба маргинала фиксированы дизайном."
        )
        avoid.append("χ² Пирсона")
        if has_zero:
            notes.append("В таблице есть нули — ещё один довод в пользу exact-теста.")
    elif n < 40:
        primary = "Барнард"
        reason = (
            f"При n = {n} (умеренная выборка, min E ≈ {min_exp:.2f}) "
            "СтатПоиск рекомендует точный критерий Барнарда. "
            "Даже при min E ≥ 5 exact-тест надёжнее χ² на малых n."
        )
        level = "recommend"
        notes.append(
            "Допустимы Бошлу и Фишер (mid-p). χ² / Йейтс — только как дополнение, не единственный вывод."
        )
        if any_exp_lt5:
            avoid.append("χ² Пирсона без поправки как единственный вывод")
    elif any_exp_lt5 or n < 100:
        if any_exp_lt5:
            primary = "Барнард"
            reason = (
                f"При n = {n} есть ожидаемые частоты < 5 (min E ≈ {min_exp:.2f}). "
                "Рекомендуется Барнард (или Бошлу); χ² Пирсона может искажать p-value."
            )
            level = "recommend"
            avoid.append("χ² Пирсона без поправки как единственный вывод")
            notes.append("Йейтс консервативнее обычного χ², но exact-тест предпочтительнее.")
        else:
            primary = "χ² Пирсона"
            reason = (
                f"При n = {n} и min E ≈ {min_exp:.2f} ≥ 5 допустим χ² Пирсона. "
                "Для отчёта полезно дублировать вывод Барнардом или Бошлу (sensitivity)."
            )
            level = "ok"
            notes.append(
                "Объём ещё не очень большой (n < 100) — exact p рядом с χ² укрепляет результат."
            )
    else:
        # n ≥ 100 and min E ≥ 5
        primary = "χ² Пирсона"
        reason = (
            f"При n = {n} и min E ≈ {min_exp:.2f} ≥ 5 основной критерий — χ² Пирсона. "
            "Exact-тесты (Фишер, Барнард, Бошлу) остаются корректными для проверки устойчивости."
        )
        level = "ok"
        notes.append(
            "На больших n p-value χ² и exact обычно близки; расхождение — повод перепроверить таблицу."
        )

    if design == "unknown":
        primary = primary + " (если группы независимы)"
        reason = (
            "Дизайн не указан. Если группы независимы: " + reason +
            " Если наблюдения парные (до/после, близнецы) — выберите «Парные» и используйте Макнемар."
        )
        level = "caution"

    if balanced_cols or balanced_rows:
        notes.append(
            "Сбалансированные маргиналы: для Барнарда удобна ориентация "
            "по равным итогам (режим «Авто» это учитывает)."
        )

    return {
        "primary": primary,
        "reason": reason,
        "level": level,
        "notes": notes,
        "avoid": avoid,
        "min_expected": float(min_exp) if min_exp == min_exp else None,
        "n": n,
        "has_zero": has_zero,
        "any_exp_lt5": bool(any_exp_lt5),
        "design": design,
    }



def calculate_all(a, b, c, d, alternative, groups="auto", design="independent"):
    table = np.array([[a, b], [c, d]])
    fisher_or, fisher_p = fisher_exact(table, alternative=alternative)

    if groups == "auto":
        groups, auto_reason = detect_orientation(a, b, c, d)
    else:
        auto_reason = None

    barnard = barnard_exact_precise(
        a, b, c, d,
        alternative=alternative,
        grid_points=1001,
        groups=groups,
    )
    mid_p, p_observed = fisher_mid_p(a, b, c, d, alternative)
    or_res = odds_ratio_ci(a, b, c, d)
    chi2_res = chi2_tests(a, b, c, d)
    mcnemar_res = mcnemar_tests(a, b, c, d)
    boschloo_res = boschloo_test(a, b, c, d, alternative=alternative)

    return {
        "fisher_or": fisher_or,
        "fisher_p": fisher_p,
        "barnard_stat": barnard["statistic"],
        "barnard_p": barnard["pvalue"],
        "barnard_pi_max": barnard["pi_max"],
        "barnard_groups": barnard["groups"],
        "barnard_auto_reason": auto_reason,
        "barnard_n1": barnard["n1"],
        "barnard_n2": barnard["n2"],
        "mid_p": mid_p,
        "p_observed": p_observed,
        "sample_or": or_res["sample_or"],
        "or": or_res["woolf_or"],
        "ci_low": or_res["ci_low"],
        "ci_high": or_res["ci_high"],
        "correction": or_res["correction"],
        "or_note": or_res["note"],
        "chi2": chi2_res["chi2"],
        "chi2_p": chi2_res["chi2_p"],
        "yates": chi2_res["yates"],
        "yates_p": chi2_res["yates_p"],
        "mcnemar_exact_p": mcnemar_res["exact_p"],
        "mcnemar_exact_stat": mcnemar_res["exact_stat"],
        "mcnemar_chi2": mcnemar_res["chi2_stat"],
        "mcnemar_chi2_p": mcnemar_res["chi2_p"],
        "mcnemar_corr": mcnemar_res["chi2_corr_stat"],
        "mcnemar_corr_p": mcnemar_res["chi2_corr_p"],
        "mcnemar_b": mcnemar_res["b"],
        "mcnemar_c": mcnemar_res["c"],
        "mcnemar_n_disc": mcnemar_res["n_discordant"],
        "boschloo_stat": boschloo_res["statistic"],
        "boschloo_p": boschloo_res["pvalue"],
        "recommendation": _enrich_recommendation_en(recommend_test(
            a, b, c, d,
            expected=chi2_res.get("expected"),
            design=design,
        )),
    }

# === PAYMENT / ОПЛАТА ===
PAYMENT_ENABLED = True
PAYMENT_TON_PRICE = 5
PAYMENT_TON_ADDRESS = "UQDr13ZRTmwK2Q6AZ2SenuC4UoxbdviZ_mtPr9FH2btlol5Q"
PAYMENT_MEMO = "StatPoisk"


def _pause_exit(code=1):
    try:
        input("\nНажмите Enter / Press Enter...")
    except Exception:
        pass
    sys.exit(code)


def ask_int(prompt, default=None):
    while True:
        try:
            msg = prompt if default is None else "%s [%s]: " % (prompt, default)
            raw = input(msg).strip()
        except EOFError:
            if default is not None:
                return default
            raise
        if raw == "" and default is not None:
            return default
        try:
            v = int(raw)
            if v < 0:
                print("  >= 0")
                continue
            return v
        except ValueError:
            print("  Integer required / Введите целое число")


def ask_menu(title, items, default_idx=1):
    print()
    print(title)
    for i, (_val, label) in enumerate(items, 1):
        star = "*" if i == default_idx else " "
        print("  %d) [%s] %s" % (i, star, label))
    while True:
        try:
            raw = input("Номер / Number [%d]: " % default_idx).strip()
        except EOFError:
            return items[default_idx - 1][0]
        if raw == "":
            return items[default_idx - 1][0]
        try:
            n = int(raw)
            if 1 <= n <= len(items):
                return items[n - 1][0]
        except ValueError:
            pass
        print("  1..%d" % len(items))


def print_report(a, b, c, d, r):
    rec = r.get("recommendation") or {}
    n = a + b + c + d

    def F(x, dig=8):
        return _fmt_num(x, dig)

    print()
    print("=" * 52)
    print("  StatPoisk / 2x2StatSearch — Results")
    print("=" * 52)
    print("  Table: [[%d, %d], [%d, %d]]   n = %d" % (a, b, c, d, n))
    print()
    if rec:
        print("  * RECOMMENDATION / РЕКОМЕНДАЦИЯ")
        print("    %s · %s" % (rec.get("primary", "-"), rec.get("primary_en", "")))
        if rec.get("reason"):
            print("   ", rec.get("reason"))
        if rec.get("reason_en"):
            print("   ", rec.get("reason_en"))
        print()
    print("  p-value")
    print("    Fisher     %s" % F(r["fisher_p"], 10))
    print("    mid-p      %s" % F(r["mid_p"], 10))
    print("    Barnard    %s" % F(r["barnard_p"], 10))
    print("    Boschloo   %s" % F(r["boschloo_p"], 10))
    print("    Chi2       %s" % F(r["chi2_p"], 10))
    print("    Yates      %s" % F(r["yates_p"], 10))
    print("    McNemar    %s (exact)" % F(r["mcnemar_exact_p"], 10))
    print()
    print("  OR")
    print("    Sample     %s" % _fmt_or(r["sample_or"]))
    print("    Woolf      %s" % _fmt_or(r["or"]))
    print("    95%% CI     [%s; %s]" % (F(r["ci_low"], 6), F(r["ci_high"], 6)))
    print("    Fisher OR  %s" % _fmt_or(r["fisher_or"]))
    print("=" * 52)
    print("  Not a substitute for a statistician.")
    print()


def main():
    print()
    print("========================================")
    print("  StatPoisk / 2x2StatSearch")
    print("  Exact tests for 2x2 tables")
    print("========================================")
    print()
    print("Table:")
    print("             Factor+    Factor-")
    print("  Group 1       a          b")
    print("  Group 2       c          d")
    print()

    a = ask_int("a (group1, +)", 7)
    b = ask_int("b (group1, -)", 12)
    c = ask_int("c (group2, +)", 8)
    d = ask_int("d (group2, -)", 3)

    if a + b + c + d == 0:
        print("Table cannot be all zeros.")
        _pause_exit(1)

    alternative = ask_menu(
        "Alternative / Альтернатива:",
        [
            ("two-sided", "two-sided OR != 1"),
            ("less", "one-sided OR < 1"),
            ("greater", "one-sided OR > 1"),
        ],
        1,
    )
    groups = ask_menu(
        "Barnard orientation / Ориентация:",
        [
            ("auto", "auto"),
            ("rows", "rows"),
            ("columns", "columns (scipy/R)"),
        ],
        1,
    )
    design = ask_menu(
        "Design / Дизайн (McNemar):",
        [
            ("independent", "independent samples"),
            ("paired", "paired / matched"),
            ("unknown", "not sure"),
        ],
        1,
    )

    print()
    print("Calculating...")
    try:
        result = calculate_all(a, b, c, d, alternative, groups, design=design)
    except Exception as e:
        print("Error:", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        _pause_exit(1)

    rec = result.get("recommendation") or {}
    if rec:
        print()
        print("* RECOMMENDATION (free)")
        print(" ", rec.get("primary"), "·", rec.get("primary_en", ""))
        if rec.get("reason"):
            print(" ", rec.get("reason"))
        if rec.get("reason_en"):
            print(" ", rec.get("reason_en"))

    if PAYMENT_ENABLED:
        print()
        print("=" * 52)
        print("  Full report: %s TON" % PAYMENT_TON_PRICE)
        print("  Network: TON")
        print("  Memo:", PAYMENT_MEMO)
        print("  Address:")
        print(" ", PAYMENT_TON_ADDRESS)
        print("=" * 52)
        try:
            ans = input("Paid? 1=yes show numbers, 0=no [0]: ").strip()
        except EOFError:
            ans = "0"
        if ans not in ("1", "y", "Y", "да", "д"):
            print("Numbers hidden. Pay and run again, choose 1.")
            try:
                input("Enter...")
            except Exception:
                pass
            return

    print_report(a, b, c, d, result)

    try:
        save = input("Save report? 1=yes 0=no [0]: ").strip()
    except EOFError:
        save = "0"
    if save in ("1", "y", "Y", "да", "д"):
        name = "statpoisk_report.txt"
        try:
            custom = input("Filename [%s]: " % name).strip()
            if custom:
                name = custom
        except EOFError:
            pass
        lines = [
            "StatPoisk / 2x2StatSearch report",
            "Table [[%d,%d],[%d,%d]] n=%d" % (a, b, c, d, a + b + c + d),
            "Alternative=%s design=%s" % (alternative, design),
            "",
            "Recommendation: %s / %s" % (rec.get("primary"), rec.get("primary_en")),
            rec.get("reason") or "",
            rec.get("reason_en") or "",
            "",
            "Fisher p = %s" % result["fisher_p"],
            "mid-p = %s" % result["mid_p"],
            "Barnard p = %s" % result["barnard_p"],
            "Boschloo p = %s" % result["boschloo_p"],
            "Chi2 p = %s" % result["chi2_p"],
            "Yates p = %s" % result["yates_p"],
            "McNemar exact p = %s" % result["mcnemar_exact_p"],
            "Woolf OR = %s" % result["or"],
            "95%% CI = [%s; %s]" % (result["ci_low"], result["ci_high"]),
        ]
        path = os.path.join(_HERE, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(str(x) for x in lines) + "\n")
        print("Saved:", path)

    try:
        input("\nPress Enter to exit...")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print("Fail:", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        _pause_exit(1)
