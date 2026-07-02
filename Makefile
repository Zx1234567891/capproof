PYTHON ?= python
PIP ?= pip
INSTALL_BIN ?= $(HOME)/.local/bin

.PHONY: install-local-hermes-wrapper uninstall-local-hermes-wrapper capproof-doctor capproof-trace capproof-trace-follow capproof-auth-queue capproof-smoke-local capproof-test-core capproof-test-full capproof-real-hermes-foreground capproof-real-hermes-ask-flow

install-local-hermes-wrapper:
	mkdir -p "$(INSTALL_BIN)"
	ln -sf "$(CURDIR)/bin/hermes" "$(INSTALL_BIN)/hermes"
	@echo "Installed $(INSTALL_BIN)/hermes -> $(CURDIR)/bin/hermes"

uninstall-local-hermes-wrapper:
	rm -f "$(INSTALL_BIN)/hermes"
	@echo "Removed $(INSTALL_BIN)/hermes"

capproof-doctor:
	$(PYTHON) tools/run_capproof_mcp_doctor.py --all

capproof-trace:
	$(PYTHON) tools/run_capproof_trace_viewer.py --latest --last 20

capproof-trace-follow:
	$(PYTHON) tools/run_capproof_trace_viewer.py --latest --follow

capproof-auth-queue:
	$(PYTHON) tools/run_capproof_auth_queue.py doctor

capproof-smoke-local:
	$(PYTHON) tools/run_capproof_mcp_server.py --list-tools
	$(PYTHON) tools/run_capproof_mcp_server.py --self-test
	$(PYTHON) tools/run_capproof_sandbox_smoke.py --local-client --scenario all

capproof-test-core:
	pytest tests/test_mcp_compatibility_profile.py -q
	pytest tests/test_claims_and_non_claims.py -q
	pytest tests/test_install_local_hermes_wrapper_docs.py -q
	pytest tests/test_artifact_reproduction_check.py -q

capproof-test-full:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest

capproof-real-hermes-foreground:
	test "$$ALLOW_HERMES_DEEPSEEK_RUN" = "1"
	test "$$ALLOW_CAPROOF_MCP_REAL_HERMES" = "1"
	test "$$ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO" = "1"
	test -n "$$DEEPSEEK_API_KEY"
	$(PYTHON) tools/run_real_hermes_foreground_mcp_demo.py --all --foreground

capproof-real-hermes-ask-flow:
	test "$$ALLOW_HERMES_DEEPSEEK_RUN" = "1"
	test "$$ALLOW_CAPROOF_MCP_REAL_HERMES" = "1"
	test "$$ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO" = "1"
	test "$$ALLOW_CAPROOF_ASK_APPROVAL_DEMO" = "1"
	test -n "$$DEEPSEEK_API_KEY"
	$(PYTHON) tools/run_real_hermes_foreground_ask_flow.py --all --foreground
