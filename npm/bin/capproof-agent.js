#!/usr/bin/env node
"use strict";

const path = require("node:path");
const { runAgentCli } = require("../lib/capproof-runner");

const invoked = path.basename(process.argv[1] || "");
runAgentCli(invoked, process.argv.slice(2));
