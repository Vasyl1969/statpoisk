(function () {
  const $ = (id) => document.getElementById(id);

  const fields = ["a", "b", "c", "d"];
  fields.forEach((id) => $(id).addEventListener("input", updateSums));
  updateSums();

  function num(id) {
    const v = parseInt($(id).value, 10);
    return Number.isFinite(v) && v >= 0 ? v : 0;
  }

  function updateSums() {
    const a = num("a"), b = num("b"), c = num("c"), d = num("d");
    $("sum-r1").textContent = a + b;
    $("sum-r2").textContent = c + d;
    $("sum-c1").textContent = a + c;
    $("sum-c2").textContent = b + d;
    $("sum-n").textContent = a + b + c + d;
  }

  function selected(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : null;
  }

  function setStatus(msg, cls) {
    const s = $("status");
    if (!msg) {
      s.hidden = true;
      return;
    }
    s.hidden = false;
    s.className = "status " + (cls || "");
    s.textContent = msg;
  }

  let lastResult = null;


  // --- Оплата TON (см. payment_config.js) ---
  function payCfg() {
    return window.PAYMENT || { enabled: false, priceTon: 5, tonAddress: "", currency: "TON", memo: "StatPoisk" };
  }

  function isUnlocked() {
    const cfg = payCfg();
    if (!cfg.enabled) return true;
    try {
      return sessionStorage.getItem("statpoisk_paid") === "1";
    } catch (e) {
      return false;
    }
  }

  function setUnlocked(v) {
    try {
      if (v) sessionStorage.setItem("statpoisk_paid", "1");
      else sessionStorage.removeItem("statpoisk_paid");
    } catch (e) {}
  }

  function tonLink(addr, amount, memo) {
    // ton:// transfer deep link
    const a = encodeURIComponent(addr || "");
    const am = encodeURIComponent(String(amount || 5));
    const t = encodeURIComponent(memo || "StatPoisk");
    return "ton://transfer/" + (addr || "") + "?amount=" + Math.round(Number(amount) * 1e9) + "&text=" + t;
  }

  function setupPaywallUI() {
    const cfg = payCfg();
    const wall = $("paywall");
    const paid = $("paid-content");
    if (!wall) return;

    if (!cfg.enabled) {
      wall.hidden = true;
      if (paid) paid.hidden = false;
      return;
    }

    const price = (cfg.priceTon || 5) + " " + (cfg.currency || "TON");
    if ($("pay-price")) $("pay-price").textContent = price;
    if ($("pay-amount")) $("pay-amount").textContent = price;
    if ($("pay-memo")) $("pay-memo").textContent = cfg.memo || "StatPoisk";
    if ($("pay-address")) $("pay-address").textContent = cfg.tonAddress || "Укажите адрес в payment_config.js";

    const link = $("btn-ton-link");
    if (link) {
      link.href = tonLink(cfg.tonAddress, cfg.priceTon, cfg.memo);
    }

    const unlocked = isUnlocked();
    wall.hidden = unlocked;
    if (paid) paid.hidden = !unlocked;
  }

  function applyPaywall() {
    const cfg = payCfg();
    const wall = $("paywall");
    const paid = $("paid-content");
    if (!cfg.enabled) {
      if (wall) wall.hidden = true;
      if (paid) paid.hidden = false;
      return;
    }
    const unlocked = isUnlocked();
    if (wall) wall.hidden = unlocked;
    if (paid) paid.hidden = !unlocked;
  }

  $("btn-calc").addEventListener("click", async () => {
    const a = num("a"), b = num("b"), c = num("c"), d = num("d");
    if (a + b + c + d === 0) {
      setStatus("Таблица не может быть нулевой · Table cannot be all zeros.", "err");
      return;
    }

    const btn = $("btn-calc");
    btn.disabled = true;
    setStatus("Считаем · Calculating (Barnard grid=1001)…", "wait");
    $("results").hidden = true;

    try {
      const res = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          a, b, c, d,
          alternative: selected("alt"),
          groups: selected("grp"),
          design: selected("design") || "independent",
        }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Ошибка сервера");
      lastResult = data.result;
      render(data.result);
      $("results").hidden = false;
      applyPaywall();
      setupPaywallUI();
      setStatus("");
    } catch (e) {
      setStatus(String(e.message || e), "err");
    } finally {
      btn.disabled = false;
    }
  });

  function enPrimary(ru) {
    const m = {
      "Барнард": "Barnard",
      "Бошлу": "Boschloo",
      "χ² Пирсона": "Pearson χ²",
      "Йейтс или Барнард": "Yates or Barnard",
      "Макнемар": "McNemar",
      "Макнемар (точный)": "McNemar (exact)",
      "недостаточно данных": "insufficient data",
    };
    let s = String(ru || "");
    for (const [k, v] of Object.entries(m)) {
      s = s.split(k).join(v);
    }
    // keep original if already mixed
    if (s === String(ru || "")) return s;
    return String(ru || "") + " · " + s;
  }

  function render(r) {
    const f = r.fmt;
    const rec = r.recommendation || {};
    const recEl = $("recommend");
    if (rec.primary) {
      recEl.hidden = false;
      recEl.className = "recommend level-" + (rec.level || "ok");
      const notesRu = (rec.notes || []).map((n) => "<li>" + esc(n) + "</li>").join("");
      const notesEn = (rec.notes_en || []).map((n) => "<li>" + esc(n) + "</li>").join("");
      const avoidRu = (rec.avoid || []).length
        ? "<p class=\"rec-notes\"><strong>Не опирайтесь только на:</strong> " + esc(rec.avoid.join(", ")) + "</p>"
        : "";
      const avoidEn = (rec.avoid_en || []).length
        ? "<p class=\"rec-notes\"><strong>Avoid relying only on:</strong> " + esc(rec.avoid_en.join(", ")) + "</p>"
        : "";
      const prim = rec.primary_en
        ? esc(rec.primary) + " · " + esc(rec.primary_en)
        : esc(enPrimary(rec.primary));
      recEl.innerHTML =
        "<div class=\"rec-title\">СтатПоиск рекомендует · Recommends: <span>" + prim + "</span></div>" +
        "<div class=\"rec-body\">" + esc(rec.reason || "") + "</div>" +
        (rec.reason_en ? "<div class=\"rec-body rec-en\">" + esc(rec.reason_en) + "</div>" : "") +
        (notesRu ? "<ul class=\"rec-notes\">" + notesRu + "</ul>" : "") +
        (notesEn ? "<ul class=\"rec-notes rec-en\">" + notesEn + "</ul>" : "") +
        avoidRu + avoidEn;

    } else {
      recEl.hidden = true;
    }
    $("metrics").innerHTML = [
      metric("Fisher p", f.fisher_p),
      metric("Barnard p", f.barnard_p),
      metric("Boschloo p", f.boschloo_p),
      metric("Woolf OR", f.woolf_or),
    ].join("");

    $("block-or").innerHTML = `
      <table>
        <tr><th>Показатель · Measure</th><th>Значение · Value</th></tr>
        <tr><td>Выборочный OR · Sample OR (ad/bc)</td><td>${esc(f.sample_or)}</td></tr>
        <tr><td>Woolf OR</td><td>${esc(f.woolf_or)}</td></tr>
        <tr><td>95% ДИ · CI (Woolf logit)</td><td>[${esc(f.ci_low)}; ${esc(f.ci_high)}]</td></tr>
        <tr><td>Fisher OR (conditional MLE)</td><td>${esc(f.fisher_or)}</td></tr>
      </table>
      <p class="note">${esc(r.or_note || "")}</p>`;

    const auto = r.barnard_auto_reason
      ? `<p class="note">Авто · Auto: ${esc(r.barnard_auto_reason)}</p>`
      : "";
    $("block-exact").innerHTML = `
      <table>
        <tr><th>Тест · Test</th><th>Статистика · Statistic</th><th>p-value</th></tr>
        <tr><td>Fisher exact</td><td>—</td><td>${esc(f.fisher_p)}</td></tr>
        <tr><td>Fisher mid-p</td><td>—</td><td>${esc(f.mid_p)}</td></tr>
        <tr><td>Barnard (${esc(r.barnard_groups)}, n₁=${r.barnard_n1}, n₂=${r.barnard_n2})</td>
            <td>${esc(f.barnard_stat)}</td><td>${esc(f.barnard_p)}</td></tr>
        <tr><td>Boschloo</td><td>${esc(f.boschloo_stat)}</td><td>${esc(f.boschloo_p)}</td></tr>
      </table>
      ${auto}
      <p class="note">π (max p, Barnard) = ${Number(r.barnard_pi_max).toFixed(4)}</p>`;

    $("block-chi2").innerHTML = `
      <table>
        <tr><th>Тест · Test</th><th>χ²</th><th>p-value</th></tr>
        <tr><td>Pearson χ²</td><td>${esc(f.chi2)}</td><td>${esc(f.chi2_p)}</td></tr>
        <tr><td>Yates corrected χ²</td><td>${esc(f.yates)}</td><td>${esc(f.yates_p)}</td></tr>
      </table>`;

    $("block-mcnemar").innerHTML = `
      <p class="warn">Только для парных данных · Paired data only (before/after, matched pairs). Independent samples → Fisher / Barnard / Boschloo.</p>
      <p class="note">Дискордантные · Discordant: b=${r.mcnemar_b}, c=${r.mcnemar_c}, n=${r.mcnemar_n_disc}</p>
      <table>
        <tr><th>Вариант · Variant</th><th>Статистика · Statistic</th><th>p-value</th></tr>
        <tr><td>Exact binomial · Точный</td><td>${r.mcnemar_exact_stat}</td><td>${esc(f.mcnemar_exact_p)}</td></tr>
        <tr><td>Asymptotic χ²</td><td>${esc(f.mcnemar_chi2)}</td><td>${esc(f.mcnemar_chi2_p)}</td></tr>
        <tr><td>χ² continuity correction</td><td>${esc(f.mcnemar_corr)}</td><td>${esc(f.mcnemar_corr_p)}</td></tr>
      </table>`;
  }

  function metric(label, value) {
    return `<div class="metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`;
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  $("btn-csv").addEventListener("click", () => {
    if (!lastResult) return;
    const r = lastResult;
    const t = r.table;
    const rows = [
      ["Показатель", "Значение"],
      ["a", t.a], ["b", t.b], ["c", t.c], ["d", t.d],
      ["Fisher p", r.fisher_p],
      ["Fisher mid-p", r.mid_p],
      ["Barnard p", r.barnard_p],
      ["Barnard statistic", r.barnard_stat],
      ["Barnard groups", r.barnard_groups],
      ["Boschloo p", r.boschloo_p],
      ["Chi2 Pearson", r.chi2],
      ["Chi2 Pearson p", r.chi2_p],
      ["Chi2 Yates", r.yates],
      ["Chi2 Yates p", r.yates_p],
      ["McNemar exact p", r.mcnemar_exact_p],
      ["McNemar chi2 p", r.mcnemar_chi2_p],
      ["McNemar corr p", r.mcnemar_corr_p],
      ["Sample OR", r.sample_or],
      ["Woolf OR", r.or],
      ["OR CI low", r.ci_low],
      ["OR CI high", r.ci_high],
      ["Fisher OR conditional", r.fisher_or],
    ];
    const csv = rows
      .map((row) =>
        row
          .map((cell) => {
            const s = cell === null || cell === undefined ? "" : String(cell);
            if (/[;"\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
            return s;
          })
          .join(";")
      )
      .join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "statpoisk_2x2.csv";
    a.click();
    URL.revokeObjectURL(url);
  });
  // Payment buttons (inside IIFE)
  if ($("btn-copy-addr")) {
    $("btn-copy-addr").addEventListener("click", async () => {
      const cfg = payCfg();
      const addr = cfg.tonAddress || "";
      try {
        await navigator.clipboard.writeText(addr);
        setStatus("Адрес скопирован · Address copied", "ok");
      } catch (e) {
        prompt("Copy address / Скопируйте адрес:", addr);
      }
    });
  }
  if ($("btn-unlock")) {
    $("btn-unlock").addEventListener("click", () => {
      const cfg = payCfg();
      if (!cfg.tonAddress || String(cfg.tonAddress).indexOf("PASTE_YOUR") >= 0) {
        setStatus("Set TON address in payment_config.js", "err");
        return;
      }
      if (confirm(
        "Confirm you sent " + (cfg.priceTon || 5) + " TON.\\n" +
        "Подтвердите перевод " + (cfg.priceTon || 5) + " TON.\\n\\n" +
        "(Manual check — verify in your wallet.)"
      )) {
        setUnlocked(true);
        applyPaywall();
        setStatus("Full report unlocked · Полный отчёт открыт", "ok");
      }
    });
  }
  setupPaywallUI();
})();
