/* ===========================================================================
   QQPilot 统一界面 —— 前端逻辑
   页面：启动台 / 运行设置 / 扩展管理 / 升级助手 / 图片导入 / 额外参数
   与 Python 的桥接：window.pywebview.api.<method>(...)（见 webui/app.py）
   =========================================================================== */
(() => {
  "use strict";

  // ---------------------------------------------------------------- state
  const state = {
    app: {},
    config: null,
    page: "launch",
    jsonTarget: "",
    translations: {},
    consoles: { upgrade: null, images: null },
  };

  // ---------------------------------------------------------------- i18n
  /** 翻译函数：T("key") 或 T("key", {name: "value"}) */
  function T(key, params) {
    let text = state.translations[key];
    if (text === undefined) text = "X" + key;
    if (params && typeof text === "string") {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      }
    }
    return text.replace('PROGRAM_NAME',state.translations['program.name']);
  }

  /** 给带 data-i18n / data-i18n-aria-label 的静态节点填入当前语言文本。 */
  function applyStaticI18n(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = T(node.dataset.i18n);
    });
    scope.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
      node.setAttribute("aria-label", T(node.dataset.i18nAriaLabel));
    });
    // CSS 里的可见文案（如控制台占位符）通过自定义属性注入
    document.documentElement.style.setProperty("--console-empty", JSON.stringify(T("ui.console.empty")));
  }

  // ------------------------------------------------------------------ dom
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "html") node.innerHTML = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("on") && typeof value === "function")
        node.addEventListener(key.slice(2).toLowerCase(), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat(4)) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  const $ = (sel) => document.querySelector(sel);

  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.7");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = ICONS[name] || "";
    return svg;
  }

  const ICONS = {
    launch: '<path d="M12 3v9"/><path d="M7.5 7.2a8 8 0 1 0 9 0"/>',
    settings:
      '<path d="M4 7h10"/><path d="M18 7h2"/><circle cx="16" cy="7" r="2"/><path d="M4 17h6"/><path d="M14 17h6"/><circle cx="12" cy="17" r="2"/>',
    extensions:
      '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9"/><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9"/><path d="M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15"/><path d="M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/><path d="M4 12h16"/>',
    upgrade:
      '<path d="M12 20V8"/><path d="m7.5 12.5 4.5-4.5 4.5 4.5"/><path d="M4 4h16"/>',
    images:
      '<rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m5 18 5-5 3 3 2-2 4 4"/>',
    json: '<path d="M8 4c-2 0-2.5 1-2.5 2.5v3C5.5 11 5 12 4 12c1 0 1.5 1 1.5 2.5v3C5.5 19 6 20 8 20"/><path d="M16 4c2 0 2.5 1 2.5 2.5v3c0 1.5.5 2.5 1.5 2.5-1 0-1.5 1-1.5 2.5v3c0 1.5-.5 2.5-2.5 2.5"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-.7 4.5"/><path d="M20 5v6h-6"/>',
    folder: '<path d="M3.5 7.5A1.5 1.5 0 0 1 5 6h3.6l1.6 2H19a1.5 1.5 0 0 1 1.5 1.5v7A1.5 1.5 0 0 1 19 18H5a1.5 1.5 0 0 1-1.5-1.5z"/>',
    save: '<path d="M5 4h11l3 3v13H5z"/><path d="M9 4v5h6"/><path d="M8 20v-6h8v6"/>',
    wand: '<path d="M5 19 17 7"/><path d="M15 5l1.2 1.2"/><path d="M19 9l1.2 1.2"/><path d="M4 7h4"/><path d="M6 5v4"/>',
  };

  // ------------------------------------------------------------------- api
  async function call(name, ...args) {
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api[name] !== "function") {
      throw new Error(T("api.not_ready"));
    }
    return api[name](...args);
  }

  // ----------------------------------------------------------------- toast
  let toastTimer = null;
  function toast(message, kind = "") {
    if (!message) return;
    const node = $("#toast");
    node.textContent = message;
    node.className = "toast show" + (kind ? ` is-${kind}` : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      node.className = "toast";
    }, 3200);
  }

  // ------------------------------------------------------------------ nav
  function getNavItems() {
    return [
      { id: "launch", label: T("ui.nav.launch") },
      { id: "settings", label: T("ui.nav.settings") },
      { id: "extensions", label: T("ui.nav.extensions") },
      { id: "upgrade", label: T("ui.nav.upgrade") },
      { id: "images", label: T("ui.nav.images") },
      { id: "json", label: T("ui.nav.json") },
    ];
  }

  function renderNav() {
    const nav = $("#nav");
    nav.replaceChildren(
      ...getNavItems().map((item) =>
        el(
          "button",
          {
            class: "nav-item",
            type: "button",
            "aria-current": state.page === item.id ? "page" : null,
            onclick: () => navigate(item.id),
          },
          icon(item.id),
          el("span", { text: item.label })
        )
      )
    );
  }

  // ------------------------------------------------------------- pilot/rail
  function setPilot(app) {
    state.app = app || {};
    const pilot = $("#pilot");
    const running = !!state.app.running;
    pilot.classList.toggle("is-running", running);
    $("#pilotState").textContent = running ? T("ui.pilot.running") : T("ui.pilot.idle");
    const bits = [];
    if (state.app.version) bits.push(`v${state.app.version}`);
    if (state.app.platform) bits.push(state.app.platform);
    $("#pilotMeta").textContent = bits.join(" · ") || "—";
    if (state.app.title) document.title = state.app.title;
    const sub = $("#brandSub");
    if (sub && state.config && state.config.name) sub.textContent = state.config.name;

    const btn = $("#railLaunch");
    btn.textContent = running ? T("ui.launch.stop_btn") : T("ui.launch.start_btn");
    btn.classList.toggle("is-stop", running);
  }

  async function refreshApp() {
    try {
      setPilot(await call("app_info"));
    } catch (_) {
      /* 忽略 */
    }
  }

  // ------------------------------------------------------------ page frame
  async function navigate(page) {
    if (!getNavItems().some((item) => item.id === page)) page = "launch";
    state.page = page;
    state.consoles.upgrade = null;
    state.consoles.images = null;
    renderNav();
    const spec = PAGES[page];
    $("#pageTitle").textContent = spec.title ? spec.title() : "";
    $("#pageLede").textContent = spec.lede ? spec.lede() : "";
    const actions = $("#pageActions");
    const view = $("#view");
    actions.replaceChildren();
    view.replaceChildren();
    try {
      await spec.mount(view, actions);
    } catch (error) {
      view.append(
        el(
          "div",
          { class: "section" },
          el("div", { class: "section-head" }, el("h2", { text: T("ui.error.page_load") })),
          el("p", { class: "lede", text: String(error && error.message ? error.message : error) })
        )
      );
    }
  }

  // ------------------------------------------------------------- factories
  function row(label, control, hint) {
    const labelCell = el(
      "div",
      { class: "field-label" },
      label,
      hint ? el("span", { class: "hint", text: hint }) : null
    );
    const fieldCell = el("div", { class: "field" }, control);
    return [labelCell, fieldCell];
  }

  function section(title, desc, ...children) {
    return el(
      "div",
      { class: "section" },
      el(
        "div",
        { class: "section-head" },
        el("h2", { text: title }),
        desc ? el("p", { text: desc }) : null
      ),
      ...children
    );
  }

  function textInput(value, opts = {}) {
    return el("input", {
      type: opts.type || "text",
      value: value === undefined || value === null ? "" : value,
      placeholder: opts.placeholder || null,
      inputmode: opts.inputmode || null,
      autocomplete: "off",
      spellcheck: "false",
    });
  }

  function textarea(value, rows = 8) {
    const node = el("textarea", { rows, spellcheck: "false" });
    node.value = value || "";
    return node;
  }

  function select(options, value) {
    const node = el("select");
    for (const opt of options) {
      node.append(
        el("option", {
          value: opt.value !== undefined ? opt.value : opt,
          text: opt.label !== undefined ? opt.label : opt,
        })
      );
    }
    node.value = value;
    return node;
  }

  function switchControl(checked, onChange) {
    const input = el("input", { type: "checkbox" });
    input.checked = !!checked;
    if (onChange) input.addEventListener("change", () => onChange(input.checked));
    const label = el("label", { class: "switch" }, input, el("span", { class: "track" }));
    label.input = input;
    return label;
  }

  function rangeControl(value, onChange) {
    const input = el("input", { type: "range", min: "0", max: "100", value: String(value) });
    const out = el("span", { class: "range-value", text: `${value}%` });
    input.addEventListener("input", () => {
      out.textContent = `${input.value}%`;
      if (onChange) onChange(input.value);
    });
    const rowNode = el("div", { class: "range-row" }, input, out);
    rowNode.input = input;
    return rowNode;
  }

  function consoleEl() {
    return el("div", { class: "console" });
  }

  function pushLine(target, text, kind = "") {
    if (!target || !document.contains(target)) return;
    const line = el("div", { class: kind ? kind : null, text });
    target.append(line);
    target.scrollTop = target.scrollHeight;
  }

  function fieldCellOf(key, ...children) {
    return el("div", { class: "field", dataset: { field: key } }, ...children);
  }

  function clearErrors(form) {
    form.querySelectorAll(".field.is-invalid").forEach((node) => node.classList.remove("is-invalid"));
    form.querySelectorAll(".field-error").forEach((node) => node.remove());
  }

  function applyErrors(form, fields) {
    clearErrors(form);
    for (const [key, message] of Object.entries(fields || {})) {
      const cell = form.querySelector(`[data-field="${key}"]`);
      if (!cell) continue;
      cell.classList.add("is-invalid");
      cell.append(el("div", { class: "field-error", text: message }));
    }
    const first = form.querySelector(".field.is-invalid");
    if (first) first.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  // ============================================================ page: launch
  const launchPage = {
    title: () => T("ui.launch.title"),
    lede: () => T("ui.launch.lede"),
    async mount(view, actions) {
      const stateLine = el("div", { class: "state" });
      const hero = el("div", { class: "hero-main" }, stateLine);
      const startBtn = el("button", { class: "btn btn-accent", type: "button" });
      const stopBtn = el("button", { class: "btn", type: "button", text: T("ui.launch.stop_btn") });
      hero.append(
        el(
          "p",
          {
            text: T("ui.launch.running_hint"),
          }
        ),
        el("div", { class: "field-row" }, startBtn, stopBtn)
      );

      const stats = el("div", { class: "hero-side" });
      const heroWrap = el("div", { class: "hero" }, hero, stats);

      const quick = el(
        "div",
        { class: "quick" },
        el("button", { type: "button", onclick: () => navigate("settings") },
          el("strong", { text: T("ui.launch.quick_settings") }), el("small", { text: T("ui.launch.quick_settings_desc") })),
        el("button", { type: "button", onclick: () => navigate("extensions") },
          el("strong", { text: T("ui.launch.quick_extensions") }), el("small", { text: T("ui.launch.quick_extensions_desc") })),
        el("button", { type: "button", onclick: () => navigate("upgrade") },
          el("strong", { text: T("ui.launch.quick_upgrade") }), el("small", { text: T("ui.launch.quick_upgrade_desc") })),
        el("button", { type: "button", onclick: () => navigate("images") },
          el("strong", { text: T("ui.launch.quick_images") }), el("small", { text: T("ui.launch.quick_images_desc") }))
      );

      const steps = section(
        T("ui.launch.howto_title"),
        T("ui.launch.howto_desc"),
        el(
          "ol",
          { class: "steps" },
          el("li", { text: T("ui.launch.howto_step1") }),
          el("li", { text: T("ui.launch.howto_step2") }),
          el("li", { text: T("ui.launch.howto_step3") })
        ),
        el("div", { class: "quick", style: "margin-top:16px" }, quick)
      );

      view.append(heroWrap, steps);

      function render() {
        const running = !!state.app.running;
        hero.classList.toggle("is-running", running);
        stateLine.replaceChildren(
          el("span", { class: "lamp" }),
          el("h2", { text: running ? T("ui.launch.running") : T("ui.launch.idle") })
        );
        startBtn.textContent = running ? T("ui.launch.restart_btn") : T("ui.launch.start_btn");
        startBtn.disabled = running;
        stopBtn.disabled = !running;
        stats.replaceChildren(
          el("dl", { class: "stat" }, el("dt", { text: T("ui.launch.stat_version") }), el("dd", { text: state.app.version ? `v${state.app.version} · ${state.app.platform}` : "—" })),
          el("dl", { class: "stat" }, el("dt", { text: T("ui.launch.stat_tokens") }), el("dd", { text: String(state.app.tokens ?? 0) })),
          el("dl", { class: "stat" }, el("dt", { text: T("ui.launch.stat_root") }), el("dd", { text: state.app.root || "—" }))
        );
      }

      startBtn.addEventListener("click", async () => {
        startBtn.disabled = true;
        try {
          const res = await call("launch");
          toast(res.message, res.ok ? "ok" : "bad");
        } catch (error) {
          toast(String(error.message || error), "bad");
        }
        await refreshApp();
        render();
      });
      stopBtn.addEventListener("click", async () => {
        const res = await call("stop");
        toast(res.message, res.ok ? "ok" : "bad");
        await refreshApp();
        render();
      });

      render();
      // 运行状态可能在别处变化，进入本页时刷新一次
      refreshApp().then(render);
      window.__launchRefresh = render;
    },
  };

  // ========================================================== page: settings
  const settingsPage = {
    title: () => T("ui.settings.title"),
    lede: () => T("ui.settings.lede"),
    async mount(view, actions) {
      const cfg = await call("get_config");
      state.config = cfg;
      const sub = $("#brandSub");
      if (sub && cfg.name) sub.textContent = cfg.name;

      const form = el("form", { class: "form", novalidate: true });
      const refs = {};
      const need = (node, key) => {
        refs[key] = node;
        return node;
      };

      // 身份
      const sIdentity = section(T("ui.settings.section_identity"), T("ui.settings.section_identity_desc"));
      const gIdentity = el("div", { class: "grid" });
      gIdentity.append(...row(T("ui.settings.username"), need(textInput(cfg.name), "name"), T("ui.settings.username_hint")));
      sIdentity.append(gIdentity);

      // 运行
      const sRun = section(T("ui.settings.section_run"), T("ui.settings.section_run_desc"));
      const gRun = el("div", { class: "grid" });
      gRun.append(...row(T("ui.settings.width"), need(textInput(cfg.width, { inputmode: "numeric" }), "width"), T("ui.settings.width_hint")));
      gRun.append(...row(T("ui.settings.height"), need(textInput(cfg.height, { inputmode: "numeric" }), "height"), T("ui.settings.height_hint")));
      gRun.append(...row(T("ui.settings.scroll"), need(textInput(cfg.scroll, { inputmode: "numeric" }), "scroll"), T("ui.settings.scroll_hint")));
      gRun.append(...row(T("ui.settings.tab_times"), need(select([{ value: "8", label: T("ui.settings.tab_times_option", { n: 8 }) }, { value: "7", label: T("ui.settings.tab_times_option", { n: 7 }) }], cfg.tab_times), "tab_times"), T("ui.settings.tab_times_hint")));
      gRun.append(...row(T("ui.settings.maximage"), need(textInput(cfg.maximagecount, { inputmode: "numeric" }), "maximagecount"), T("ui.settings.maximage_hint")));
      gRun.append(...row(T("ui.settings.sendimagepossibility"), need(rangeControl(cfg.sendimagepossibility), "sendimagepossibility"), T("ui.settings.sendimagepossibility_hint")));
      gRun.append(...row(T("ui.settings.autologin"), switchControl(cfg.autologin), T("ui.settings.autologin_hint")));
      gRun.append(...row(T("ui.settings.autofocusing"), switchControl(cfg.autofocusing), T("ui.settings.autofocusing_hint")));
      gRun.append(...row(T("ui.settings.withimage"), switchControl(cfg.withimage), T("ui.settings.withimage_hint")));
      gRun.append(...row(T("ui.settings.atdetect"), switchControl(cfg.atdetect), T("ui.settings.atdetect_hint")));
      sRun.append(gRun);

      // 模型与服务器
      const sModel = section(T("ui.settings.section_model"), T("ui.settings.section_model_desc"));
      const gModel = el("div", { class: "grid" });
      gModel.append(...row(T("ui.settings.modelname"), need(textInput(cfg.modelname), "modelname")));
      gModel.append(...row(T("ui.settings.vision_model"), switchControl(cfg.isvisionmodel), T("ui.settings.vision_model_hint")));

      const customRow = row(T("ui.settings.custom_url"), need(textInput(cfg.custom_server_url, { placeholder: "http://192.168.1.100:8000/v1" }), "custom_server_url"), T("ui.settings.custom_url_hint"));
      const onebotGrid = el("div", { class: "grid" });
      onebotGrid.append(...row(T("ui.settings.ws_server"), need(textInput(cfg.websocket_server), "websocket_server"), T("ui.settings.ws_server_hint")));
      onebotGrid.append(...row(T("ui.settings.account_id"), need(textInput(cfg.account_id), "account_id"), T("ui.settings.account_id_hint")));
      onebotGrid.append(...row(T("ui.settings.reverse"), switchControl(cfg.reverse), T("ui.settings.reverse_hint")));
      const onebotBlock = el(
        "div",
        { class: "section", style: "margin:6px 0 0;padding:18px 0 0;border:0;border-top:1px solid var(--line);border-radius:0;background:transparent" },
        el("div", { class: "section-head" }, el("h2", { text: T("ui.settings.section_onebot") }), el("p", { text: T("ui.settings.section_onebot_desc") })),
        onebotGrid
      );

      const segmented = el("div", { class: "segmented", role: "group", "aria-label": T("ui.settings.server") });
      const modeButtons = {};
      const setMode = (mode) => {
        for (const [key, btn] of Object.entries(modeButtons)) {
          btn.setAttribute("aria-pressed", key === mode ? "true" : "false");
        }
        customRow[0].hidden = customRow[1].hidden = mode !== "custom";
        onebotBlock.hidden = mode !== "onebot";
      };
      for (const mode of [
        { id: "ollama", label: T("ui.settings.server_ollama") },
        { id: "builtin", label: T("ui.settings.server_builtin") },
        { id: "onebot", label: T("ui.settings.server_onebot") },
        { id: "custom", label: T("ui.settings.server_custom") },
      ]) {
        const btn = el("button", { type: "button", text: mode.label, onclick: () => { state.config.server_mode = mode.id; setMode(mode.id); } });
        modeButtons[mode.id] = btn;
        segmented.append(btn);
      }
      gModel.append(...row(T("ui.settings.server"), segmented, T("ui.settings.server_hint")));
      gModel.append(...customRow);
      gModel.append(...row(T("ui.settings.api_key"), need(passwordInput(cfg.api_key), "api_key"), T("ui.settings.api_key_hint")));
      gModel.append(...row(T("ui.settings.force_ollama"), switchControl(cfg.forceollamaapi), T("ui.settings.force_ollama_hint")));
      gModel.append(...row(T("ui.settings.remote_timeout"), need(textInput(cfg.remote_server_timeout, { inputmode: "numeric" }), "remote_server_timeout"), T("ui.settings.remote_timeout_hint")));
      sModel.append(gModel, onebotBlock);
      setMode(cfg.server_mode);

      // 提示词
      const sPrompt = section(T("ui.settings.section_prompt"), T("ui.settings.section_prompt_desc"));
      const gPrompt = el("div", { class: "grid" });
      const systemBox = need(textarea(cfg.system, 10), "system");
      systemBox.style.fontFamily = "var(--font-mono)";
      systemBox.style.fontSize = "12.8px";
      gPrompt.append(
        ...row(T("ui.settings.system"), systemBox),
        el("div", { class: "field-label" }, T("ui.settings.extra_params")),
        fieldCellOf(
          "extra",
          el("button", {
            class: "btn btn-sm",
            type: "button",
            onclick: () => navigate("json"),
            text: T("ui.settings.edit_extra"),
          }),
          el("div", { class: "inline-note", style: "margin-top:6px" }, T("ui.settings.extra_params_hint"))
        )
      );
      sPrompt.append(gPrompt);

      form.append(sIdentity, sRun, sModel, sPrompt);

      // 给每个可校验字段的 .field 单元格打上 data-field，供错误回显定位
      for (const [key, node] of Object.entries(refs)) {
        const cell = node && node.closest && node.closest(".field");
        if (cell) cell.dataset.field = key;
      }

      // 底部操作
      const saveBottom = el("button", { class: "btn btn-accent", type: "submit", text: T("ui.settings.save_btn") });
      form.append(el("div", { class: "field-row", style: "margin-top:6px" }, saveBottom));

      actions.append(
        el("button", { class: "btn btn-quiet", type: "button", text: T("ui.settings.reload"), onclick: () => navigate("settings") }),
        el("button", { class: "btn btn-primary", type: "button", text: T("ui.settings.save"), onclick: () => form.requestSubmit() })
      );

      function collect() {
        const on = (key) => !!(refs[key] && refs[key].input && refs[key].input.checked);
        return {
          name: refs.name.value.trim(),
          width: refs.width.value.trim(),
          height: refs.height.value.trim(),
          maximagecount: refs.maximagecount.value.trim(),
          scroll: refs.scroll.value.trim(),
          tab_times: refs.tab_times.value,
          modelname: refs.modelname.value.trim(),
          isvisionmodel: on("isvisionmodel"),
          server_mode: state.config.server_mode,
          custom_server_url: refs.custom_server_url.value.trim(),
          api_key: refs.api_key.value,
          forceollamaapi: on("forceollamaapi"),
          remote_server_timeout: refs.remote_server_timeout.value.trim(),
          withimage: on("withimage"),
          autologin: on("autologin"),
          autofocusing: on("autofocusing"),
          sendimagepossibility: Number((refs.sendimagepossibility.input || {}).value || 0),
          atdetect: on("atdetect"),
          system: refs.system.value,
          websocket_server: refs.websocket_server.value.trim(),
          account_id: refs.account_id.value.trim(),
          reverse: on("reverse"),
        };
      }

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        saveBottom.disabled = true;
        try {
          const res = await call("save_config", collect());
          applyErrors(form, res.fields);
          toast(res.message, res.ok ? "ok" : "bad");
          if (res.ok) await refreshApp();
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          saveBottom.disabled = false;
        }
      });

      view.append(form);
    },
  };

  function passwordInput(value) {
    const input = textInput(value, { type: "password" });
    const toggle = el("button", { class: "btn btn-sm", type: "button", text: T("ui.settings.show") });
    toggle.addEventListener("click", () => {
      const hidden = input.type === "password";
      input.type = hidden ? "text" : "password";
      toggle.textContent = hidden ? T("ui.settings.hide") : T("ui.settings.show");
    });
    return el("div", { class: "field-row" }, input, toggle);
  }

  // ======================================================== page: extensions
  const extensionsPage = {
    title: () => T("ui.ext.title"),
    lede: () => T("ui.ext.lede"),
    async mount(view, actions) {
      const status = el("p", { class: "lede", text: T("ui.ext.loading") });
      const list = el("div", { class: "list" });
      const head = section(T("ui.ext.section"), T("ui.ext.section_desc"), list);
      head.append(status);
      view.append(head);

      async function refresh() {
        const res = await call("list_extensions");
        const items = res.items || [];
        list.replaceChildren(
          ...(items.length
            ? items.map((item) =>
                el(
                  "div",
                  { class: "list-item" + (item.enabled ? "" : " is-off") },
                  el(
                    "div",
                    { class: "grow" },
                    el("div", { class: "name", text: item.name }),
                    el("div", { class: "desc", text: item.description })
                  ),
                  el("span", { class: "tag " + (item.enabled ? "on" : "off"), text: item.enabled ? T("ui.ext.status_enabled") : T("ui.ext.status_disabled") }),
                  el("button", {
                    class: "btn btn-sm",
                    type: "button",
                    text: item.enabled ? T("ui.ext.btn_disable") : T("ui.ext.btn_enable"),
                    onclick: async (event) => {
                      event.target.disabled = true;
                      const result = await call("set_extension", item.name, !item.enabled);
                      toast(result.message, result.ok ? "ok" : "bad");
                      await refresh();
                    },
                  })
                )
              )
            : [el("div", { class: "list-item" }, el("div", { class: "grow" }, el("div", { class: "name", text: T("ui.ext.empty") }), el("div", { class: "desc", text: T("ui.ext.empty_hint") })))])
        );
        status.textContent = items.length ? T("ui.ext.count", { count: items.length }) : T("ui.ext.dir_empty");
        if (res.dir) state.extDir = res.dir;
      }

      function renderItems() {
        refresh();
      }

      actions.append(
        el("button", { class: "btn", type: "button", onclick: () => { refresh(); toast(T("ui.ext.refreshed")); } }, icon("refresh"), el("span", { text: T("ui.ext.btn_refresh") })),
        el("button", { class: "btn", type: "button", onclick: () => call("open_path", "Extensions") }, icon("folder"), el("span", { text: T("ui.ext.btn_open_dir") }))
      );

      await refresh();
    },
  };

  // =========================================================== page: upgrade
  const upgradePage = {
    title: () => T("ui.upgrade.title"),
    lede: () => T("ui.upgrade.lede"),
    async mount(view, actions) {
      const source = textInput(state.app.root || "", {});
      source.readOnly = true;
      const dest = textInput("", { placeholder: T("ui.upgrade.dest_placeholder") });
      const log = consoleEl();
      state.consoles.upgrade = log;

      const pick = el("button", {
        class: "btn",
        type: "button",
        onclick: async () => {
          const res = await call("pick_folder", T("ui.upgrade.pick_title"));
          if (res && res.ok && res.path) dest.value = res.path;
          else if (res && !res.ok) toast(res.error || T("folder.pick_failed"), "bad");
        },
      }, icon("folder"), el("span", { text: T("ui.upgrade.btn_pick") }));

      const start = el("button", { class: "btn btn-accent", type: "button", text: T("ui.upgrade.btn_start") });
      start.addEventListener("click", async () => {
        if (!dest.value.trim()) {
          toast(T("ui.upgrade.err_no_dest"), "bad");
          return;
        }
        start.disabled = true;
        log.replaceChildren();
        try {
          const res = await call("start_upgrade", dest.value.trim());
          toast(res.message, res.ok ? "ok" : "bad");
          pushLine(log, res.message, res.ok ? "ok" : "bad");
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          start.disabled = false;
        }
      });

      const grid = el("div", { class: "grid" });
      grid.append(
        ...row(T("ui.upgrade.source"), source, T("ui.upgrade.source_hint")),
        el("div", { class: "field-label" }, T("ui.upgrade.dest")),
        el("div", { class: "field" }, el("div", { class: "field-row" }, dest, pick))
      );

      view.append(
        section(T("ui.upgrade.section"), T("ui.upgrade.section_desc"), grid,
          el("div", { class: "field-row", style: "margin-top:18px" }, start)),
        section(T("ui.upgrade.log"), null, log)
      );
    },
  };

  // ============================================================ page: images
  const imagesPage = {
    title: () => T("ui.images.title"),
    lede: () => T("ui.images.lede"),
    async mount(view, actions) {
      const source = textInput("", { placeholder: T("ui.images.source_placeholder") });
      const log = consoleEl();
      state.consoles.images = log;

      const pick = el("button", {
        class: "btn",
        type: "button",
        onclick: async () => {
          const res = await call("pick_folder", T("ui.images.pick_title"));
          if (res && res.ok && res.path) source.value = res.path;
          else if (res && !res.ok) toast(res.error || T("folder.pick_failed"), "bad");
        },
      }, icon("folder"), el("span", { text: T("ui.images.btn_pick") }));

      const start = el("button", { class: "btn btn-accent", type: "button", text: T("ui.images.btn_start") });
      start.addEventListener("click", async () => {
        if (!source.value.trim()) {
          toast(T("ui.images.err_no_source"), "bad");
          return;
        }
        start.disabled = true;
        log.replaceChildren();
        try {
          const res = await call("import_images", source.value.trim());
          toast(res.message, res.ok ? "ok" : "bad");
          pushLine(log, res.message, res.ok ? "ok" : "bad");
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          start.disabled = false;
        }
      });

      const grid = el("div", { class: "grid" });
      grid.append(
        el("div", { class: "field-label" }, T("ui.images.source")),
        el("div", { class: "field" }, el("div", { class: "field-row" }, source, pick)),
        el("div", { class: "field-label" }, T("ui.images.target")),
        el("div", { class: "field" }, el("div", { class: "inline-note", text: T("ui.images.target_hint") }))
      );

      actions.append(
        el("button", { class: "btn btn-quiet", type: "button", onclick: () => call("open_path", "Images") }, icon("folder"), el("span", { text: T("ui.images.btn_open") }))
      );

      view.append(
        section(T("ui.images.section"), T("ui.images.section_desc"), grid,
          el("div", { class: "field-row", style: "margin-top:18px" }, start)),
        section(T("ui.images.progress"), null, log)
      );
    },
  };

  // ============================================================== page: json
  const jsonPage = {
    title: () => T("ui.json.title"),
    lede: () => T("ui.json.lede"),
    async mount(view, actions) {
      const target = state.jsonTarget || "extra.json";
      const pathInput = textInput(target);
      const editor = textarea("", 16);
      editor.style.fontFamily = "var(--font-mono)";
      editor.style.fontSize = "12.8px";
      const status = el("p", { class: "lede", text: "" });

      async function load() {
        const res = await call("read_json", pathInput.value.trim() || "extra.json");
        if (!res.ok) {
          status.textContent = res.error || T("json.read_failed");
          return;
        }
        editor.value = res.text || "";
        status.textContent = res.exists ? T("ui.json.status_loaded", { path: res.path }) : T("ui.json.status_new", { path: res.path });
      }

      const format = el("button", {
        class: "btn",
        type: "button",
        onclick: () => {
          try {
            editor.value = JSON.stringify(JSON.parse(editor.value || "{}"), null, 4);
            status.textContent = T("json.format_ok");
          } catch (error) {
            status.textContent = T("ui.json.parse_failed", { msg: error.message });
          }
        },
      }, icon("wand"), el("span", { text: T("ui.json.btn_format") }));

      const save = el("button", { class: "btn btn-accent", type: "button", text: T("ui.json.btn_save") });
      save.addEventListener("click", async () => {
        save.disabled = true;
        try {
          const res = await call("write_json", { path: pathInput.value.trim() || target, text: editor.value });
          toast(res.message, res.ok ? "ok" : "bad");
          if (res.ok) status.textContent = T("ui.json.status_saved", { path: res.path });
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          save.disabled = false;
        }
      });

      pathInput.addEventListener("change", load);

      const grid = el("div", { class: "grid" });
      grid.append(
        el("div", { class: "field-label" }, T("ui.json.file")),
        fieldCellOf("path", pathInput),
        el("div", { class: "field-label" }, T("ui.json.content")),
        fieldCellOf("text", editor)
      );

      actions.append(format, save);
      view.append(
        section(T("ui.json.section_title"), T("ui.json.content_desc"), grid, status,
          el("div", { class: "field-row", style: "margin-top:16px" }, format, save))
      );

      await load();
    },
  };

  const PAGES = {
    launch: launchPage,
    settings: settingsPage,
    extensions: extensionsPage,
    upgrade: upgradePage,
    images: imagesPage,
    json: jsonPage,
  };

  // --------------------------------------------------------- python events
  window.UI = {
    emit(event, payload) {
      if (event === "upgrade:log") pushLine(state.consoles.upgrade, payload && payload.text);
      else if (event === "images:log") pushLine(state.consoles.images, payload && payload.text);
    },
  };

  // ------------------------------------------------------------------- boot
  async function init() {
    try {
      const boot = await call("bootstrap");
      state.jsonTarget = boot.jsonTarget || "";
      state.translations = boot.translations || {};
      if (boot.language) document.documentElement.lang = String(boot.language).replace("_", "-");
      applyStaticI18n();
      setPilot(boot.app);
      $("#brandSub").textContent = (boot.app && boot.app.onebot) ? "onebot" : "neko";
      $("#railLaunch").addEventListener("click", async () => {
        const btn = $("#railLaunch");
        btn.disabled = true;
        try {
          const res = state.app.running ? await call("stop") : await call("launch");
          toast(res.message, res.ok ? "ok" : "bad");
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          btn.disabled = false;
          await refreshApp();
          if (window.__launchRefresh && state.page === "launch") window.__launchRefresh();
        }
      });
      await navigate(boot.page || "launch");
      $("#boot").classList.add("hide");
    } catch (error) {
      $("#bootText").textContent = T("ui.boot.failed", { msg: error.message || error });
    }
  }

  function start() {
    if (window.pywebview && window.pywebview.api) {
      init();
      return;
    }
    window.addEventListener("pywebviewready", init, { once: true });
    setTimeout(() => {
      if (!window.pywebview) {
        $("#bootText").textContent = T("ui.boot.open_in_window");
      }
    }, 2500);
  }

  document.addEventListener("DOMContentLoaded", start);
})();
