"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..", "..");

const AGENT_SCRIPTS = {
  hermes: "tools/run_hermes_capproof_foreground.py",
  opencode: "tools/run_opencode_capproof_foreground.py",
  openclaw: "tools/run_openclaw_capproof_foreground.py",
  codewhale: "tools/run_codewhale_capproof_foreground.py"
};

function packageJson() {
  return JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
}

function findPython() {
  const candidates = [process.env.CAPPROOF_PYTHON, "python3", "python"].filter(Boolean);
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }
  return null;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    env: process.env,
    stdio: options.stdio || "inherit",
    encoding: options.encoding || "utf8",
    shell: false
  });
  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  process.exit(result.status === null ? 1 : result.status);
}

function capture(command, args) {
  return spawnSync(command, args, {
    cwd: ROOT,
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
    shell: false
  });
}

function runPythonScript(script, args) {
  const python = findPython();
  if (!python) {
    console.error("Python 3.11+ was not found. Set CAPPROOF_PYTHON to the Python executable.");
    process.exit(1);
  }
  run(python, [path.join(ROOT, script), ...args]);
}

function printHelp() {
  const version = packageJson().version;
  console.log(`CapProof MCP ${version}

Usage:
  capproof-mcp setup
  capproof-mcp doctor [--json]
  capproof-mcp list-tools
  capproof-mcp serve
  capproof-mcp trace
  capproof-mcp trace-follow
  capproof-mcp auth-queue [list|doctor|...]
  capproof-mcp bootstrap-runtimes [args...]
  capproof-mcp runtime-gate [args...]
  capproof-mcp agent <hermes|opencode|openclaw|codewhale> [args...]

Installed agent commands:
  hermes
  opencode
  openclaw
  codewhale

Security:
  DEEPSEEK_API_KEY is read from the environment only.
  The npm wrapper does not write API keys to config, logs, traces, or reports.
  CapProof uses the existing standard MCP server and does not fork guard logic.
`);
}

function printSetup() {
  const python = findPython();
  const keyPresent = Boolean(process.env.DEEPSEEK_API_KEY);
  let toolsCount = "unknown";
  if (python) {
    const result = capture(python, [path.join(ROOT, "tools/run_capproof_mcp_server.py"), "--list-tools"]);
    if (result.status === 0) {
      try {
        const payload = JSON.parse(result.stdout);
        const tools = Array.isArray(payload) ? payload : payload.tools;
        toolsCount = Array.isArray(tools) ? String(tools.length) : "unknown";
      } catch {
        toolsCount = "unknown";
      }
    }
  }
  console.log([
    "CapProof MCP npm package is installed.",
    `python_available=${python ? "true" : "false"}`,
    `deepseek_api_key_present=${keyPresent ? "true" : "false"}`,
    "deepseek_key_source=DEEPSEEK_API_KEY",
    "deepseek_key_written=false",
    "standard_mcp_server=tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution",
    `exposed_tools=${toolsCount}`,
    "agent_commands=hermes,opencode,openclaw,codewhale",
    "next=run capproof-mcp doctor or start an agent command"
  ].join("\n"));
}

function runCapproofCli(argv) {
  const [command, ...rest] = argv;
  if (!command || command === "help" || command === "--help" || command === "-h") {
    printHelp();
    return;
  }
  if (command === "version" || command === "--version" || command === "-v") {
    console.log(packageJson().version);
    return;
  }
  if (command === "setup") {
    printSetup();
    return;
  }
  if (command === "doctor") {
    runPythonScript("tools/run_capproof_mcp_doctor.py", rest.length ? rest : ["--all"]);
  }
  if (command === "list-tools") {
    runPythonScript("tools/run_capproof_mcp_server.py", ["--list-tools", ...rest]);
  }
  if (command === "self-test") {
    runPythonScript("tools/run_capproof_mcp_server.py", ["--self-test", ...rest]);
  }
  if (command === "serve" || command === "stdio" || command === "mcp-server") {
    runPythonScript("tools/run_capproof_mcp_server.py", ["--stdio", "--sandboxed-real-execution", ...rest]);
  }
  if (command === "trace") {
    runPythonScript("tools/run_capproof_trace_viewer.py", rest.length ? rest : ["--latest", "--last", "20"]);
  }
  if (command === "trace-follow") {
    runPythonScript("tools/run_capproof_trace_viewer.py", rest.length ? rest : ["--latest", "--follow"]);
  }
  if (command === "auth-queue") {
    runPythonScript("tools/run_capproof_auth_queue.py", rest.length ? rest : ["doctor"]);
  }
  if (command === "runtime-gate") {
    runPythonScript("tools/run_agent_runtime_gate.py", rest.length ? rest : ["--all", "--require-real-policy", "--report"]);
  }
  if (command === "bootstrap-runtimes") {
    runPythonScript("tools/run_agent_runtime_bootstrap.py", rest.length ? rest : ["--preflight"]);
  }
  if (command === "parity-matrix") {
    runPythonScript("tools/run_agent_parity_matrix.py", rest.length ? rest : ["--report"]);
  }
  if (command === "real-evaluator") {
    runPythonScript("tools/run_real_agent_parity_evaluator.py", rest);
  }
  if (command === "agent") {
    const [agent, ...agentArgs] = rest;
    runAgentCli(agent, agentArgs);
    return;
  }
  if (Object.prototype.hasOwnProperty.call(AGENT_SCRIPTS, command)) {
    runAgentCli(command, rest);
    return;
  }
  console.error(`Unknown command: ${command}`);
  printHelp();
  process.exit(2);
}

function normalizeAgentName(invoked) {
  const base = (invoked || "").replace(/^capproof-/, "");
  if (Object.prototype.hasOwnProperty.call(AGENT_SCRIPTS, base)) {
    return base;
  }
  return "";
}

function runAgentCli(invoked, argv) {
  const agent = normalizeAgentName(invoked);
  if (!agent) {
    console.error("Expected agent name: hermes, opencode, openclaw, or codewhale.");
    process.exit(2);
  }
  runPythonScript(AGENT_SCRIPTS[agent], argv);
}

module.exports = {
  ROOT,
  runCapproofCli,
  runAgentCli
};
