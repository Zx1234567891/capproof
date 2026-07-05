#!/usr/bin/env node
"use strict";

const { runCapproofCli } = require("../lib/capproof-runner");

runCapproofCli(process.argv.slice(2));
