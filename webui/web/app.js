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
    consoles: { upgrade: null, images: null },
  };

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
      throw new Error("桌面窗口尚未就绪");
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
  const NAV = [
    { id: "launch", label: "启动台" },
    { id: "settings", label: "运行设置" },
    { id: "extensions", label: "扩展管理" },
    { id: "upgrade", label: "升级助手" },
    { id: "images", label: "图片导入" },
    { id: "json", label: "额外参数" },
  ];

  function renderNav() {
    const nav = $("#nav");
    nav.replaceChildren(
      ...NAV.map((item) =>
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
    $("#pilotState").textContent = running ? "正在运行" : "未运行";
    const bits = [];
    if (state.app.version) bits.push(`v${state.app.version}`);
    if (state.app.platform) bits.push(state.app.platform);
    $("#pilotMeta").textContent = bits.join(" · ") || "—";
    if (state.app.title) document.title = state.app.title;
    const sub = $("#brandSub");
    if (sub && state.config && state.config.name) sub.textContent = state.config.name;

    const btn = $("#railLaunch");
    btn.textContent = running ? "停止 QQPilot" : "启动 QQPilot";
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
    if (!NAV.some((item) => item.id === page)) page = "launch";
    state.page = page;
    state.consoles.upgrade = null;
    state.consoles.images = null;
    renderNav();
    const spec = PAGES[page];
    $("#pageTitle").textContent = spec.title;
    $("#pageLede").textContent = spec.lede;
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
          el("div", { class: "section-head" }, el("h2", { text: "这一页没能加载" })),
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
    title: "启动台",
    lede: "让 QQPilot 接管屏幕：读取消息、请求模型、发送回复。",
    async mount(view, actions) {
      const stateLine = el("div", { class: "state" });
      const hero = el("div", { class: "hero-main" }, stateLine);
      const startBtn = el("button", { class: "btn btn-accent", type: "button" });
      const stopBtn = el("button", { class: "btn", type: "button", text: "停止" });
      hero.append(
        el(
          "p",
          {
            text: "启动后 QQPilot 会持续框选屏幕上的新消息，按你的设置请求模型，并把回复发回对话。",
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
          el("strong", { text: "运行设置" }), el("small", { text: "模型、服务器、提示词" })),
        el("button", { type: "button", onclick: () => navigate("extensions") },
          el("strong", { text: "扩展管理" }), el("small", { text: "启用或停用扩展" })),
        el("button", { type: "button", onclick: () => navigate("upgrade") },
          el("strong", { text: "升级助手" }), el("small", { text: "部署到其他目录" })),
        el("button", { type: "button", onclick: () => navigate("images") },
          el("strong", { text: "图片导入" }), el("small", { text: "批量复制图片素材" }))
      );

      const steps = section(
        "第一次使用",
        "QQPilot 依赖一个能看懂聊天记录的语言模型，或者一个 OneBot 机器人后端。",
        el(
          "ol",
          { class: "steps" },
          el("li", { text: "在“运行设置”里选好服务器：Ollama、内置模型、OneBot 直连，或任意 Chat Completion 地址。" }),
          el("li", { text: "打开 QQ，把要处理的聊天窗口停在屏幕上的固定位置。" }),
          el("li", { text: "回到这里点“启动”，QQPilot 会自己完成剩下的循环。" })
        ),
        el("div", { class: "quick", style: "margin-top:16px" }, quick)
      );

      view.append(heroWrap, steps);

      function render() {
        const running = !!state.app.running;
        hero.classList.toggle("is-running", running);
        stateLine.replaceChildren(
          el("span", { class: "lamp" }),
          el("h2", { text: running ? "QQPilot 正在运行" : "QQPilot 未运行" })
        );
        startBtn.textContent = running ? "重新启动" : "启动 QQPilot";
        startBtn.disabled = running;
        stopBtn.disabled = !running;
        stats.replaceChildren(
          el("dl", { class: "stat" }, el("dt", { text: "版本" }), el("dd", { text: state.app.version ? `v${state.app.version} · ${state.app.platform}` : "—" })),
          el("dl", { class: "stat" }, el("dt", { text: "Token 用量" }), el("dd", { text: String(state.app.tokens ?? 0) })),
          el("dl", { class: "stat" }, el("dt", { text: "安装目录" }), el("dd", { text: state.app.root || "—" }))
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
    title: "运行设置",
    lede: "这些值会写回 config.ini，下次启动生效。",
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
      const sIdentity = section("身份", "程序用用户名判断哪些消息是自己发出去的。");
      const gIdentity = el("div", { class: "grid" });
      gIdentity.append(...row("用户名", need(textInput(cfg.name), "name"), "与 QQ 里的昵称一致"));
      sIdentity.append(gIdentity);

      // 运行
      const sRun = section("运行", "控制截图框选与回复节奏。");
      const gRun = el("div", { class: "grid" });
      gRun.append(...row("窗口宽度", need(textInput(cfg.width, { inputmode: "numeric" }), "width"), "QQ 窗口的像素宽度"));
      gRun.append(...row("窗口高度", need(textInput(cfg.height, { inputmode: "numeric" }), "height"), "QQ 窗口的像素高度"));
      gRun.append(...row("框选消息时长（秒）", need(textInput(cfg.scroll, { inputmode: "numeric" }), "scroll"), "拖动框选聊天记录时按住的时间"));
      gRun.append(...row("按下 Tab 次数", need(select([{ value: "8", label: "8 次" }, { value: "7", label: "7 次" }], cfg.tab_times), "tab_times"), "框选时总是点到删除等按键时，试试改成 7"));
      gRun.append(...row("解析图片数", need(textInput(cfg.maximagecount, { inputmode: "numeric" }), "maximagecount"), "本地模型解析多张图片会明显变慢"));
      gRun.append(...row("发送图片概率", need(rangeControl(cfg.sendimagepossibility), "sendimagepossibility"), "答案为空时，按这个概率改为发送图片"));
      gRun.append(...row("自动点击登录", switchControl(cfg.autologin), "启动后自动点掉登录按钮"));
      gRun.append(...row("持续置于最前", switchControl(cfg.autofocusing), "不断把 QQ 窗口拉到最前面"));
      gRun.append(...row("包含图片", switchControl(cfg.withimage), "把聊天里的图片一起交给模型"));
      gRun.append(...row("只检查 @", switchControl(cfg.atdetect), "只有被 @ 的消息才回复"));
      sRun.append(gRun);

      // 模型与服务器
      const sModel = section("模型与服务器", "决定回复由谁生成。");
      const gModel = el("div", { class: "grid" });
      gModel.append(...row("模型名称", need(textInput(cfg.modelname), "modelname")));
      gModel.append(...row("视觉模型", switchControl(cfg.isvisionmodel), "模型能否理解图片"));

      const customRow = row("自定义地址", need(textInput(cfg.custom_server_url, { placeholder: "http://192.168.1.100:8000/v1" }), "custom_server_url"), "填到 /v1 为止的 base URL");
      const onebotGrid = el("div", { class: "grid" });
      onebotGrid.append(...row("WebSocket 地址", need(textInput(cfg.websocket_server), "websocket_server"), "OneBot v11 的 WS 地址"));
      onebotGrid.append(...row("机器人账号", need(textInput(cfg.account_id), "account_id"), "可随意填写，需与 OneBot 端一致"));
      onebotGrid.append(...row("反向连接", switchControl(cfg.reverse), "开启=本机监听等 OneBot 连入；关闭=主动连出去"));
      const onebotBlock = el(
        "div",
        { class: "section", style: "margin:6px 0 0;padding:18px 0 0;border:0;border-top:1px solid var(--line);border-radius:0;background:transparent" },
        el("div", { class: "section-head" }, el("h2", { text: "OneBot 直连" }), el("p", { text: "api_key 会作为 CompletionConnector 的 authorization。" })),
        onebotGrid
      );

      const segmented = el("div", { class: "segmented", role: "group", "aria-label": "服务器" });
      const modeButtons = {};
      const setMode = (mode) => {
        for (const [key, btn] of Object.entries(modeButtons)) {
          btn.setAttribute("aria-pressed", key === mode ? "true" : "false");
        }
        customRow[0].hidden = customRow[1].hidden = mode !== "custom";
        onebotBlock.hidden = mode !== "onebot";
      };
      for (const mode of [
        { id: "ollama", label: "Ollama" },
        { id: "builtin", label: "内置模型" },
        { id: "onebot", label: "OneBot" },
        { id: "custom", label: "自定义" },
      ]) {
        const btn = el("button", { type: "button", text: mode.label, onclick: () => { state.config.server_mode = mode.id; setMode(mode.id); } });
        modeButtons[mode.id] = btn;
        segmented.append(btn);
      }
      gModel.append(...row("服务器", segmented, "选择回复的来源"));
      gModel.append(...customRow);
      gModel.append(...row("API Key", need(passwordInput(cfg.api_key), "api_key"), "OneBot 模式下作为 authorization"));
      gModel.append(...row("强制 Ollama API", switchControl(cfg.forceollamaapi), "即使地址不是 ollama，也按 /api/chat 调用"));
      gModel.append(...row("远程超时（秒）", need(textInput(cfg.remote_server_timeout, { inputmode: "numeric" }), "remote_server_timeout"), "等待模型或 OneBot 回复的最长时间"));
      sModel.append(gModel, onebotBlock);
      setMode(cfg.server_mode);

      // 提示词
      const sPrompt = section("提示词", "system 会作为第一条 system 消息发给模型。");
      const gPrompt = el("div", { class: "grid" });
      const systemBox = need(textarea(cfg.system, 10), "system");
      systemBox.style.fontFamily = "var(--font-mono)";
      systemBox.style.fontSize = "12.8px";
      gPrompt.append(
        ...row("system", systemBox),
        el("div", { class: "field-label" }, "额外参数"),
        fieldCellOf(
          "extra",
          el("button", {
            class: "btn btn-sm",
            type: "button",
            onclick: () => navigate("json"),
            text: "编辑 extra.json",
          }),
          el("div", { class: "inline-note", style: "margin-top:6px" }, "会合并进请求体，用于 temperature 等自定义字段")
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
      const saveBottom = el("button", { class: "btn btn-accent", type: "submit", text: "保存设置" });
      form.append(el("div", { class: "field-row", style: "margin-top:6px" }, saveBottom));

      actions.append(
        el("button", { class: "btn btn-quiet", type: "button", text: "重新载入", onclick: () => navigate("settings") }),
        el("button", { class: "btn btn-primary", type: "button", text: "保存", onclick: () => form.requestSubmit() })
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
    const toggle = el("button", { class: "btn btn-sm", type: "button", text: "显示" });
    toggle.addEventListener("click", () => {
      const hidden = input.type === "password";
      input.type = hidden ? "text" : "password";
      toggle.textContent = hidden ? "隐藏" : "显示";
    });
    return el("div", { class: "field-row" }, input, toggle);
  }

  // ======================================================== page: extensions
  const extensionsPage = {
    title: "扩展管理",
    lede: "扩展是 Extensions/ 下的 Python 文件；停用会把文件改名为 .disabled。",
    async mount(view, actions) {
      const status = el("p", { class: "lede", text: "正在加载…" });
      const list = el("div", { class: "list" });
      const head = section("已安装的扩展", "改动在下一次启动时生效。", list);
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
                  el("span", { class: "tag " + (item.enabled ? "on" : "off"), text: item.enabled ? "启用" : "禁用" }),
                  el("button", {
                    class: "btn btn-sm",
                    type: "button",
                    text: item.enabled ? "停用" : "启用",
                    onclick: async (event) => {
                      event.target.disabled = true;
                      const result = await call("set_extension", item.name, !item.enabled);
                      toast(result.message, result.ok ? "ok" : "bad");
                      await refresh();
                    },
                  })
                )
              )
            : [el("div", { class: "list-item" }, el("div", { class: "grow" }, el("div", { class: "name", text: "还没有扩展" }), el("div", { class: "desc", text: "把 .py 文件放进 Extensions/ 目录即可。" })))])
        );
        status.textContent = items.length ? `共 ${items.length} 个扩展` : "目录为空";
        if (res.dir) state.extDir = res.dir;
      }

      function renderItems() {
        refresh();
      }

      actions.append(
        el("button", { class: "btn", type: "button", onclick: () => { refresh(); toast("已刷新"); } }, icon("refresh"), el("span", { text: "刷新" })),
        el("button", { class: "btn", type: "button", onclick: () => call("open_path", "Extensions") }, icon("folder"), el("span", { text: "打开目录" }))
      );

      await refresh();
    },
  };

  // =========================================================== page: upgrade
  const upgradePage = {
    title: "升级助手",
    lede: "把当前目录的代码复制到目标安装目录；目标已有的 config.ini 与个人配置会被保留。",
    async mount(view, actions) {
      const source = textInput(state.app.root || "", {});
      source.readOnly = true;
      const dest = textInput("", { placeholder: "选择要升级到的安装目录" });
      const log = consoleEl();
      state.consoles.upgrade = log;

      const pick = el("button", {
        class: "btn",
        type: "button",
        onclick: async () => {
          const res = await call("pick_folder", "选择目标文件夹");
          if (res && res.ok && res.path) dest.value = res.path;
          else if (res && !res.ok) toast(res.error || "无法打开文件夹选择", "bad");
        },
      }, icon("folder"), el("span", { text: "选择文件夹" }));

      const start = el("button", { class: "btn btn-accent", type: "button", text: "开始升级" });
      start.addEventListener("click", async () => {
        if (!dest.value.trim()) {
          toast("请先选择目标文件夹", "bad");
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
        ...row("源目录", source, "就是程序当前所在的位置"),
        el("div", { class: "field-label" }, "目标目录"),
        el("div", { class: "field" }, el("div", { class: "field-row" }, dest, pick))
      );

      view.append(
        section("升级到另一个目录", "适合把开发目录的改动同步到正式运行的安装目录。", grid,
          el("div", { class: "field-row", style: "margin-top:18px" }, start)),
        section("操作日志", null, log)
      );
    },
  };

  // ============================================================ page: images
  const imagesPage = {
    title: "图片导入",
    lede: "把某个文件夹里的图片批量复制到程序的 Images/ 目录。",
    async mount(view, actions) {
      const source = textInput("", { placeholder: "选择包含图片的文件夹" });
      const log = consoleEl();
      state.consoles.images = log;

      const pick = el("button", {
        class: "btn",
        type: "button",
        onclick: async () => {
          const res = await call("pick_folder", "选择包含图片的文件夹");
          if (res && res.ok && res.path) source.value = res.path;
          else if (res && !res.ok) toast(res.error || "无法打开文件夹选择", "bad");
        },
      }, icon("folder"), el("span", { text: "选择文件夹" }));

      const start = el("button", { class: "btn btn-accent", type: "button", text: "开始复制" });
      start.addEventListener("click", async () => {
        if (!source.value.trim()) {
          toast("请先选择源文件夹", "bad");
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
        el("div", { class: "field-label" }, "源文件夹"),
        el("div", { class: "field" }, el("div", { class: "field-row" }, source, pick)),
        el("div", { class: "field-label" }, "目标目录"),
        el("div", { class: "field" }, el("div", { class: "inline-note", text: "Images/（程序目录下）" }))
      );

      actions.append(
        el("button", { class: "btn btn-quiet", type: "button", onclick: () => call("open_path", "Images") }, icon("folder"), el("span", { text: "打开 Images" }))
      );

      view.append(
        section("导入图片", "支持 jpg、png、gif、bmp、webp、tiff、svg。同名文件会被覆盖。", grid,
          el("div", { class: "field-row", style: "margin-top:18px" }, start)),
        section("进度", null, log)
      );
    },
  };

  // ============================================================== page: json
  const jsonPage = {
    title: "额外参数",
    lede: "直接编辑交给模型的额外请求参数；保存前会先校验 JSON。",
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
          status.textContent = res.error || "读取失败";
          return;
        }
        editor.value = res.text || "";
        status.textContent = res.exists ? `已载入 ${res.path}` : `${res.path} 还不存在，保存后会创建`;
      }

      const format = el("button", {
        class: "btn",
        type: "button",
        onclick: () => {
          try {
            editor.value = JSON.stringify(JSON.parse(editor.value || "{}"), null, 4);
            status.textContent = "已格式化";
          } catch (error) {
            status.textContent = `JSON 解析失败：${error.message}`;
          }
        },
      }, icon("wand"), el("span", { text: "格式化" }));

      const save = el("button", { class: "btn btn-accent", type: "button", text: "保存" });
      save.addEventListener("click", async () => {
        save.disabled = true;
        try {
          const res = await call("write_json", { path: pathInput.value.trim() || target, text: editor.value });
          toast(res.message, res.ok ? "ok" : "bad");
          if (res.ok) status.textContent = `已保存 ${res.path}`;
        } catch (error) {
          toast(String(error.message || error), "bad");
        } finally {
          save.disabled = false;
        }
      });

      pathInput.addEventListener("change", load);

      const grid = el("div", { class: "grid" });
      grid.append(
        el("div", { class: "field-label" }, "文件"),
        fieldCellOf("path", pathInput),
        el("div", { class: "field-label" }, "内容"),
        fieldCellOf("text", editor)
      );

      actions.append(format, save);
      view.append(
        section("JSON 内容", "这里的内容会合并进每次请求体，可覆盖同名键（如 temperature）。", grid, status,
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
      $("#bootText").textContent = `无法连接桌面窗口：${error.message || error}`;
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
        $("#bootText").textContent = "请通过 QQPilot 桌面窗口打开本界面。";
      }
    }, 2500);
  }

  document.addEventListener("DOMContentLoaded", start);
})();
