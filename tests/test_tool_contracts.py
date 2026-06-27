from capproof import (
    AuthorityRole,
    ToolContract,
    default_tool_contract_registry,
    default_tool_contracts,
)


def field_roles(contract: ToolContract) -> dict[str, AuthorityRole]:
    return {field.name: field.role for field in contract.authority}


def test_default_registry_contains_five_mvp_tools() -> None:
    registry = default_tool_contract_registry()
    tools = {contract.tool for contract in registry.all()}

    assert tools == {"read_file", "summarize", "send_email", "write_file", "run_shell"}


def test_send_email_bcc_authority() -> None:
    contract = default_tool_contract_registry().require("send_email")
    roles = field_roles(contract)

    assert roles["bcc"] == AuthorityRole.RECIPIENT
    assert "bcc" in contract.coverage_fields
    assert "bcc" in contract.high_impact_fields


def test_send_email_cc_reply_to_headers_authority() -> None:
    contract = default_tool_contract_registry().require("send_email")
    roles = field_roles(contract)

    assert roles["cc"] == AuthorityRole.RECIPIENT
    assert roles["reply_to"] == AuthorityRole.RECIPIENT
    assert roles["headers"] == AuthorityRole.CREDENTIAL
    assert {"cc", "reply_to", "headers"} <= set(contract.coverage_fields)


def test_send_email_attachment_authority() -> None:
    contract = default_tool_contract_registry().require("send_email")
    roles = field_roles(contract)

    assert roles["attachments"] == AuthorityRole.FILE_PATH
    assert "attachments" in contract.coverage_fields
    assert "attachments" in contract.high_impact_fields


def test_write_file_symlink_policy_is_explicit() -> None:
    contract = default_tool_contract_registry().require("write_file")

    assert contract.metadata["symlink_policy"] == "resolve_and_deny_escape"
    assert "path" in contract.coverage_fields


def test_run_shell_contract_is_template_only() -> None:
    contract = default_tool_contract_registry().require("run_shell")
    roles = field_roles(contract)

    assert roles["command_template"] == AuthorityRole.COMMAND
    assert roles["cwd"] == AuthorityRole.FILE_PATH
    assert roles["env"] == AuthorityRole.CREDENTIAL
    assert roles["stdin"] == AuthorityRole.CONTENT
    assert contract.metadata["arbitrary_shell"] is False
    assert contract.metadata["canonicalization_claim"] == "allowlisted_template_membership_only"


def test_all_contracts_are_stably_serializable() -> None:
    contracts = default_tool_contracts()

    for contract in contracts:
        decoded = ToolContract.from_dict(contract.to_dict())
        assert decoded == contract
        assert decoded.to_canonical_json() == contract.to_canonical_json()
