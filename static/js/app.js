(() => {
  "use strict";

  const PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
  const URLS = Object.freeze({
    add: "https://gist.githubusercontent.com/mdecourse/0229a8a017091476a79700b8a190f185/raw/c48e37714f055c3a0027cbfef59e442a6ef659b9/from_1_add_to_100_1.py",
    ode: "https://gist.githubusercontent.com/mdecycu/ec4bb35dd0769e7a83d2a9fa57878a67/raw/98d582539545b3c9fbfa35dd3e605c506367618e/pyodide_ode_ex1.py",
    robot: "https://gist.githubusercontent.com/mdecycu/ec4bb35dd0769e7a83d2a9fa57878a67/raw/9d164526e5f0fedbdcab913cb8bb180c0cb462a8/pyodide_robot_ex1.py",
    walk: "https://gist.githubusercontent.com/mdecycu/ec4bb35dd0769e7a83d2a9fa57878a67/raw/8655bed2bf5c8dfa6e6d776d7b09264f1ed23d47/pyodide_robot_ex3.py"
  });

  let pyodide = null;
  let editor1 = null;
  let editor2 = null;
  let executionQueue = Promise.resolve();
  let initialized = false;

  const $ = (id) => document.getElementById(id);
  const editorConfig = {
    theme: "ace/theme/chrome",
    mode: "ace/mode/python",
    fontSize: 14,
    showPrintMargin: false,
    tabSize: 4,
    useSoftTabs: true,
    enableBasicAutocompletion: true,
    enableLiveAutocompletion: true,
    enableSnippets: true
  };

  function setStatus(message, state = "") {
    $("runtime_status_text").textContent = message;
    $("runtime_status").className = `runtime-status ${state}`.trim();
  }

  function setReadyButtons(ready) {
    document.querySelectorAll("button").forEach((button) => {
      if (button.id !== "reload_page" && button.id !== "kw_output1" &&
          button.id !== "kw_output2" && button.id !== "kw_clear_console1" &&
          button.id !== "kw_clear_console2") {
        button.disabled = !ready;
      }
    });
  }

  function createEditors() {
    if (!window.ace) throw new Error("Ace Editor 未載入，請檢查 /static/ace/ace.js 路徑。");
    editor1 = ace.edit("kw_editor1", editorConfig);
    editor2 = ace.edit("kw_editor2", editorConfig);
    editor1.setValue("", -1);
    editor2.setValue("", -1);
    editor1.focus();
  }

  async function fetchText(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`讀取範例失敗：HTTP ${response.status} (${url})`);
    return response.text();
  }

  // src 只允許已知範例網址，避免任意 URL 被當作程式碼來源。
  function isKnownSource(value) {
    return Object.values(URLS).includes(value);
  }

  async function installRobotModule() {
    const candidates = ["/static/robot.py", "/downloads/robot.py"];
    for (const url of candidates) {
      try {
        const source = await fetchText(url);
        if (!source.trim()) continue;
        pyodide.FS.writeFile("robot.py", source);
        console.info(`robot 模組已載入：${url}`);
        return true;
      } catch (error) {
        console.warn(`略過 robot 模組來源 ${url}`, error);
      }
    }
    console.warn("找不到 robot.py；一般 Python、NumPy 等功能仍可使用。");
    return false;
  }

  async function initializePyodide() {
    if (initialized) return;
    setStatus("正在載入 Python 執行環境…");
    createEditors();

    if (typeof loadPyodide !== "function") {
      throw new Error("Pyodide 腳本未載入，請檢查 CDN 網路連線。");
    }

    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });
    setStatus("正在載入 NumPy、SciPy、Matplotlib…");
    await pyodide.loadPackage(["numpy", "scipy", "matplotlib", "micropip"]);

    pyodide.runPython(`
def hello():
    print("Hello from custom module! (模組定義於本網頁)")
`);
    await installRobotModule();

    const params = new URLSearchParams(window.location.search);
    const requestedSource = params.get("src");
    const sourceUrl = isKnownSource(requestedSource) ? requestedSource : URLS.add;
    try {
      if (requestedSource === "inline_hello") {
        editor1.setValue("hello()", -1);
      } else if (requestedSource === "inline_version") {
        editor1.setValue(
`import pyodide
import sys
import matplotlib
import numpy
import scipy

print("Pyodide version:", pyodide.__version__)
print("Python version :", sys.version)
print("Matplotlib version:", matplotlib.__version__)
print("NumPy version:", numpy.__version__)
print("SciPy version:", scipy.__version__)
`, -1);
      } else {
        editor1.setValue(await fetchText(sourceUrl), -1);
        if (sourceUrl !== requestedSource) updateSourceUrl(sourceUrl);
      }
    } catch (error) {
      editor1.setValue('print("Pyodide 已載入，請輸入 Python 程式後按執行。")', -1);
      appendOutput("kw_console1", `範例載入提醒：${error.message}\n`);
    }

    initialized = true;
    setReadyButtons(true);
    setStatus("Python 執行環境已就緒", "ready");
  }

  function updateSourceUrl(value) {
    const url = new URL(window.location.href);
    url.searchParams.set("src", value);
    window.history.replaceState({}, "", url);
  }

  function appendOutput(consoleId, value) {
    const area = $(consoleId);
    area.value += value;
    area.scrollTop = area.scrollHeight;
  }

  function clearOutput(consoleId, visualId) {
    $(consoleId).value = "";
    $(visualId).replaceChildren();
  }

  function enqueue(task) {
    // 所有 Python 執行都共用同一個佇列，避免 stdout/stderr 互相覆蓋。
    const next = executionQueue.then(task, task);
    executionQueue = next.catch(() => {});
    return next;
  }

  async function runPython(editor, consoleId, visualId, stateId) {
    if (!initialized || !pyodide) {
      appendOutput(consoleId, "Python 執行環境尚未準備完成。\n");
      return;
    }

    return enqueue(async () => {
      const runButton = consoleId === "kw_console1" ? $("kw_run1") : $("kw_run2");
      runButton.disabled = true;
      $(stateId).textContent = "執行中…";
      $(consoleId).value = "";
      $(visualId).replaceChildren();

      const write = (message) => appendOutput(consoleId, message);
      pyodide.setStdout({ batched: write });
      pyodide.setStderr({ batched: (message) => write(message) });

      try {
        await pyodide.runPythonAsync(editor.getValue());
      } catch (error) {
        write(`\n執行錯誤：${error.message || String(error)}\n`);
        console.error(error);
      } finally {
        // 下一個工作執行前會重新指定輸出接收器。
        $(stateId).textContent = "執行完成";
        runButton.disabled = false;
      }
    });
  }

  async function loadExample(url, editor, shouldRun = true) {
    try {
      const source = await fetchText(url);
      editor.setValue(source, -1);
      if (editor === editor1) updateSourceUrl(url);
      if (shouldRun) {
        const isFirst = editor === editor1;
        await runPython(
          editor,
          isFirst ? "kw_console1" : "kw_console2",
          isFirst ? "brython_div1" : "brython_div2",
          isFirst ? "run_state1" : "run_state2"
        );
      }
    } catch (error) {
      const target = editor === editor1 ? "kw_console1" : "kw_console2";
      appendOutput(target, `\n載入範例失敗：${error.message}\n`);
    }
  }

  function showOutput(consoleId) {
    const area = $(consoleId);
    area.rows = 18;
    area.scrollIntoView({ behavior: "smooth", block: "nearest" });
    area.focus();
  }

  function bindEvents() {
    $("version").addEventListener("click", () => {
      editor1.setValue(
`import pyodide
import sys
import matplotlib
import numpy
import scipy

print("Pyodide version:", pyodide.__version__)
print("Python version :", sys.version)
print("Matplotlib version:", matplotlib.__version__)
print("NumPy version:", numpy.__version__)
print("SciPy version:", scipy.__version__)
`, -1);
      updateSourceUrl("inline_version");
      runPython(editor1, "kw_console1", "brython_div1", "run_state1");
    });

    $("hello_button").addEventListener("click", () => {
      editor1.setValue("hello()", -1);
      updateSourceUrl("inline_hello");
      runPython(editor1, "kw_console1", "brython_div1", "run_state1");
    });

    $("add1to100").addEventListener("click", () => loadExample(URLS.add, editor1));
    $("numpy_ode").addEventListener("click", () => loadExample(URLS.ode, editor1));
    $("robot1").addEventListener("click", () => loadExample(URLS.robot, editor1));
    $("free_walk").addEventListener("click", () => loadExample(URLS.walk, editor1));
    $("add1to100part2").addEventListener("click", () => loadExample(URLS.add, editor2, false));

    $("kw_run1").addEventListener("click", () =>
      runPython(editor1, "kw_console1", "brython_div1", "run_state1"));
    $("kw_run2").addEventListener("click", () =>
      runPython(editor2, "kw_console2", "brython_div2", "run_state2"));

    $("kw_clear_console1").addEventListener("click", () =>
      clearOutput("kw_console1", "brython_div1"));
    $("kw_clear_console2").addEventListener("click", () =>
      clearOutput("kw_console2", "brython_div2"));
    $("kw_output1").addEventListener("click", () => showOutput("kw_console1"));
    $("kw_output2").addEventListener("click", () => showOutput("kw_console2"));
    $("reload_page").addEventListener("click", () => window.location.reload());
  }

  document.addEventListener("DOMContentLoaded", async () => {
    bindEvents();
    setReadyButtons(false);
    try {
      await initializePyodide();
    } catch (error) {
      console.error(error);
      setStatus("載入失敗，請檢查網路與資源路徑", "error");
      appendOutput("kw_console1", `初始化錯誤：${error.message || String(error)}\n`);
    }
  });
})();
