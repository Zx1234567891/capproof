"""Tool contract registry for the CapProof MVP tools."""

from __future__ import annotations

from dataclasses import dataclass

from capproof.schemas import AuthorityField, AuthorityRole, ToolContract


@dataclass
class ToolContractRegistry:
    """In-memory registry of trusted tool contracts."""

    _contracts: dict[str, ToolContract]

    def __init__(self, contracts: tuple[ToolContract, ...] = ()) -> None:
        self._contracts = {}
        for contract in contracts:
            self.register(contract)

    def register(self, contract: ToolContract) -> None:
        if contract.tool in self._contracts:
            raise ValueError(f"tool contract already registered: {contract.tool}")
        self._contracts[contract.tool] = contract

    def get(self, tool: str) -> ToolContract | None:
        return self._contracts.get(tool)

    def require(self, tool: str) -> ToolContract:
        contract = self.get(tool)
        if contract is None:
            raise KeyError(f"unknown tool contract: {tool}")
        return contract

    def all(self) -> tuple[ToolContract, ...]:
        return tuple(self._contracts[name] for name in sorted(self._contracts))


def default_tool_contracts() -> tuple[ToolContract, ...]:
    return (
        read_file_contract(),
        summarize_contract(),
        send_email_contract(),
        write_file_contract(),
        run_shell_contract(),
    )


def default_tool_contract_registry() -> ToolContractRegistry:
    return ToolContractRegistry(default_tool_contracts())


def read_file_contract() -> ToolContract:
    return ToolContract(
        tool="read_file",
        args_schema={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "role": AuthorityRole.FILE_PATH.value, "access": "read"},
            },
            "additionalProperties": False,
        },
        authority=(
            AuthorityField(name="path", role=AuthorityRole.FILE_PATH, access="read"),
        ),
        side_effects=("reads(path)",),
        coverage_fields=("path",),
        high_impact_fields=("path",),
        metadata={"symlink_policy": "resolve_and_deny_escape"},
    )


def summarize_contract() -> ToolContract:
    return ToolContract(
        tool="summarize",
        args_schema={
            "type": "object",
            "required": ["input"],
            "properties": {
                "input": {"type": "string", "role": AuthorityRole.CONTENT.value},
            },
            "additionalProperties": False,
        },
        authority=(
            AuthorityField(
                name="input",
                role=AuthorityRole.CONTENT,
                required=True,
                high_impact=False,
            ),
        ),
        side_effects=(),
        coverage_fields=("input",),
        high_impact_fields=(),
        metadata={"pure_transform": True},
    )


def send_email_contract() -> ToolContract:
    return ToolContract(
        tool="send_email",
        args_schema={
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to": {"type": "string", "role": AuthorityRole.RECIPIENT.value},
                "cc": {"type": "array", "items": {"type": "string"}},
                "bcc": {"type": "array", "items": {"type": "string"}},
                "reply_to": {"type": "string", "role": AuthorityRole.RECIPIENT.value},
                "headers": {"type": "object", "role": AuthorityRole.CREDENTIAL.value},
                "subject": {"type": "string", "role": AuthorityRole.CONTENT.value},
                "body": {"type": "string", "role": AuthorityRole.CONTENT.value},
                "attachments": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        authority=(
            AuthorityField(name="to", role=AuthorityRole.RECIPIENT),
            AuthorityField(name="cc", role=AuthorityRole.RECIPIENT, required=False),
            AuthorityField(name="bcc", role=AuthorityRole.RECIPIENT, required=False),
            AuthorityField(name="reply_to", role=AuthorityRole.RECIPIENT, required=False),
            AuthorityField(name="headers", role=AuthorityRole.CREDENTIAL, required=False),
            AuthorityField(name="subject", role=AuthorityRole.CONTENT, high_impact=False),
            AuthorityField(name="body", role=AuthorityRole.CONTENT, high_impact=False),
            AuthorityField(
                name="attachments",
                role=AuthorityRole.FILE_PATH,
                required=False,
                access="read",
            ),
        ),
        side_effects=("egress(to,cc,bcc)", "routes(reply_to,headers)", "reads(attachments)"),
        coverage_fields=("to", "cc", "bcc", "reply_to", "headers", "attachments"),
        high_impact_fields=("to", "cc", "bcc", "reply_to", "headers", "attachments"),
    )


def write_file_contract() -> ToolContract:
    return ToolContract(
        tool="write_file",
        args_schema={
            "type": "object",
            "required": ["path", "content", "mode", "overwrite"],
            "properties": {
                "path": {"type": "string", "role": AuthorityRole.FILE_PATH.value, "access": "write"},
                "content": {"type": "string", "role": AuthorityRole.CONTENT.value},
                "mode": {"type": "string", "enum": ["create", "append", "overwrite"]},
                "overwrite": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        authority=(
            AuthorityField(name="path", role=AuthorityRole.FILE_PATH, access="write"),
            AuthorityField(name="content", role=AuthorityRole.CONTENT, high_impact=False),
            AuthorityField(name="mode", role=AuthorityRole.COMMAND),
            AuthorityField(name="overwrite", role=AuthorityRole.COMMAND),
        ),
        side_effects=("writes(path)",),
        coverage_fields=("path", "content", "mode", "overwrite"),
        high_impact_fields=("path", "mode", "overwrite"),
        metadata={"symlink_policy": "resolve_and_deny_escape"},
    )


def run_shell_contract() -> ToolContract:
    return ToolContract(
        tool="run_shell",
        args_schema={
            "type": "object",
            "required": ["command_template", "args", "cwd", "env", "stdin"],
            "properties": {
                "command_template": {"type": "string", "role": AuthorityRole.COMMAND.value},
                "args": {"type": "object"},
                "cwd": {"type": "string", "role": AuthorityRole.FILE_PATH.value},
                "env": {"type": "object", "role": AuthorityRole.CREDENTIAL.value},
                "stdin": {"type": ["string", "null"], "role": AuthorityRole.CONTENT.value},
            },
            "additionalProperties": False,
        },
        authority=(
            AuthorityField(name="command_template", role=AuthorityRole.COMMAND),
            AuthorityField(name="args", role=AuthorityRole.COMMAND),
            AuthorityField(name="cwd", role=AuthorityRole.FILE_PATH),
            AuthorityField(name="env", role=AuthorityRole.CREDENTIAL),
            AuthorityField(name="stdin", role=AuthorityRole.CONTENT, required=False),
        ),
        side_effects=("executes(command_template,args,cwd,env,stdin)",),
        coverage_fields=("command_template", "args", "cwd", "env", "stdin"),
        high_impact_fields=("command_template", "args", "cwd", "env", "stdin"),
        metadata={
            "arbitrary_shell": False,
            "canonicalization_claim": "allowlisted_template_membership_only",
        },
    )
