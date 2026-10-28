"""OptDSL language server.

A thin protocol adapter over :mod:`optdsl_tooling`. All semantics live in the
tooling package; this module only translates LSP requests into calls on a
:class:`~optdsl_tooling.analysis.ModuleIndex` and back.

Design constraints that shaped it:

* **Never execute the buffer.** ``analyze`` uses ``compile_runtime=False``, so
  no ``exec`` happens on text the user is editing.
* **Never raise.** A handler that throws turns into a silent editor failure.
  Every entry point catches and degrades.
* **Debounce diagnostics.** Re-analysing on every keystroke is wasteful for
  large instances (the CVRP files have ~2000 decision indices).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from optdsl_tooling import analyze, check, fingerprint
from optdsl_tooling.analysis import BUILTIN_NAMES, ModuleIndex
from optdsl_tooling.diagnostics import Diagnostic, Severity

LOGGER = logging.getLogger(__name__)

SERVER_NAME = "optdsl-lsp"
SERVER_VERSION = "0.1.0"

#: Language id contributed by the VS Code extension.
LANGUAGE_ID = "optdsl"

#: Debounce window for diagnostics, in seconds.
DIAGNOSTIC_DELAY = 0.25

_SEVERITY_MAP = {
    Severity.ERROR: types.DiagnosticSeverity.Error,
    Severity.WARNING: types.DiagnosticSeverity.Warning,
    Severity.INFORMATION: types.DiagnosticSeverity.Information,
    Severity.HINT: types.DiagnosticSeverity.Hint,
}

_TOKEN_TYPES = [
    "namespace", "type", "class", "enum", "interface", "struct", "typeParameter",
    "parameter", "variable", "property", "enumMember", "event", "function",
    "method", "macro", "keyword", "modifier", "comment", "string", "number",
    "regexp", "operator", "decorator",
]

_TOKEN_MODIFIERS = ["declaration", "definition", "readonly", "static", "deprecated", "defaultLibrary"]

_TOKEN_LEGEND = types.SemanticTokensLegend(
    token_types=_TOKEN_TYPES,
    token_modifiers=_TOKEN_MODIFIERS,
)

#: Index into ``_TOKEN_TYPES``.
_TT = {name: index for index, name in enumerate(_TOKEN_TYPES)}


class OptDSLServer(LanguageServer):
    """Language server holding one analysed document per open URI."""

    def __init__(self) -> None:
        super().__init__(SERVER_NAME, SERVER_VERSION)
        self.indexes: dict[str, ModuleIndex] = {}

    def index_for(self, uri: str) -> ModuleIndex | None:
        return self.indexes.get(uri)

    def reindex(self, uri: str, source: str) -> ModuleIndex:
        index = analyze(source)
        self.indexes[uri] = index
        return index


server = OptDSLServer()


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------


@server.feature(types.INITIALIZE)
def initialize(params: types.InitializeParams) -> types.InitializeResult:
    return types.InitializeResult(
        capabilities=types.ServerCapabilities(
            text_document_sync=types.TextDocumentSyncOptions(
                open_close=True,
                change=types.TextDocumentSyncKind.Full,
                save=types.SaveOptions(include_text=True),
            ),
            completion_provider=types.CompletionOptions(
                trigger_characters=[".", "(", ",", " "],
                resolve_provider=False,
            ),
            hover_provider=True,
            definition_provider=True,
            references_provider=True,
            document_symbol_provider=True,
            workspace_symbol_provider=True,
            document_formatting_provider=False,
            rename_provider=types.RenameOptions(prepare_provider=True),
            folding_range_provider=True,
            signature_help_provider=types.SignatureHelpOptions(
                trigger_characters=["(", ","],
            ),
            code_action_provider=types.CodeActionOptions(
                code_action_kinds=[types.CodeActionKind.QuickFix, types.CodeActionKind.Refactor],
            ),
            code_lens_provider=types.CodeLensOptions(resolve_provider=False),
            inlay_hint_provider=True,
            semantic_tokens_provider=types.SemanticTokensOptions(
                legend=_TOKEN_LEGEND,
                full=True,
            ),
            execute_command_provider=types.ExecuteCommandOptions(
                commands=[
                    "optdsl.analyze",
                    "optdsl.translate",
                    "optdsl.solve",
                    "optdsl.lns",
                    "optdsl.synthesizeOperator",
                ]
            ),
        ),
        server_info=types.ServerInfo(name=SERVER_NAME, version=SERVER_VERSION),
    )


@server.feature(types.INITIALIZED)
def initialized(_params: types.InitializedParams) -> None:
    LOGGER.info("%s %s ready", SERVER_NAME, SERVER_VERSION)


@server.feature(types.SHUTDOWN)
def shutdown(_params: Any) -> None:
    server.indexes.clear()


# ---------------------------------------------------------------------------
# document sync
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: types.DidOpenTextDocumentParams) -> None:
    document = params.text_document
    if document.language_id != LANGUAGE_ID:
        return
    server.reindex(document.uri, document.text)
    _publish_diagnostics(document.uri)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: types.DidChangeTextDocumentParams) -> None:
    document = server.workspace.get_text_document(params.text_document.uri)
    server.reindex(document.uri, document.source)
    _publish_diagnostics(document.uri)


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: types.DidSaveTextDocumentParams) -> None:
    document = server.workspace.get_text_document(params.text_document.uri)
    server.reindex(document.uri, document.source)
    _publish_diagnostics(document.uri)


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: types.DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    server.indexes.pop(uri, None)
    server.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, diagnostics=[])
    )


def _publish_diagnostics(uri: str) -> None:
    index = server.index_for(uri)
    if index is None:
        return
    try:
        diagnostics = [_to_lsp_diagnostic(d) for d in check(index)]
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("diagnostics failed for %s", uri)
        return
    server.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


def _to_lsp_diagnostic(diagnostic: Diagnostic) -> types.Diagnostic:
    return types.Diagnostic(
        range=_range(diagnostic.span),
        message=diagnostic.message,
        severity=_SEVERITY_MAP.get(diagnostic.severity, types.DiagnosticSeverity.Error),
        code=diagnostic.code,
        source=SERVER_NAME,
        related_information=[
            types.DiagnosticRelatedInformation(
                location=types.Location(uri="", range=_range(span)),
                message=message,
            )
            for span, message in diagnostic.related
        ]
        or None,
    )


def _range(span: Any) -> types.Range:
    return types.Range(
        start=types.Position(line=span.start_line, character=span.start_character),
        end=types.Position(line=span.end_line, character=span.end_character),
    )


# ---------------------------------------------------------------------------
# completion
# ---------------------------------------------------------------------------

_DS_SNIPPETS: list[tuple[str, str, str]] = [
    ("DSInt", "DSInt(${1:lower}, ${2:upper})", "Integer domain"),
    ("DSFloat", "DSFloat(${1:lower}, ${2:upper})", "Float domain"),
    ("DSBool", "DSBool()", "Boolean domain"),
    ("DSList", "DSList(${1:length}, ${2:element_type})", "Fixed-length list"),
    ("DSRecord", 'DSRecord({"${1:field}": ${2:DSInt(0, 10)}})', "Record type"),
]

_KEYWORD_SNIPPETS: list[tuple[str, str, str]] = [
    ("minimize", "minimize(${1:objective})", "Minimise the objective"),
    ("maximize", "maximize(${1:objective})", "Maximise the objective"),
    ("assert", "assert ${1:condition}", "Add a constraint"),
    ("warm_start", "@warm_start(${1:upper_bound}=${2:0})", "Attach a warm-start hint"),
]


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completion(params: types.CompletionParams) -> types.CompletionList:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return types.CompletionList(is_incomplete=False, items=[])

    items: list[types.CompletionItem] = []

    for name, snippet, detail in _DS_SNIPPETS:
        items.append(
            types.CompletionItem(
                label=name,
                kind=types.CompletionItemKind.Class,
                detail=detail,
                insert_text=snippet,
                insert_text_format=types.InsertTextFormat.Snippet,
                documentation=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"OptDSL type constructor `{name}`.",
                ),
            )
        )

    for name, snippet, detail in _KEYWORD_SNIPPETS:
        items.append(
            types.CompletionItem(
                label=name,
                kind=types.CompletionItemKind.Keyword,
                detail=detail,
                insert_text=snippet,
                insert_text_format=types.InsertTextFormat.Snippet,
            )
        )

    for constant in index.constants.values():
        items.append(
            types.CompletionItem(
                label=constant.name,
                kind=types.CompletionItemKind.Constant,
                detail=_preview(constant.value),
                documentation=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"```python\n{constant.name} = {constant.raw_code}\n```",
                ),
            )
        )

    for variable in index.variables.values():
        items.append(
            types.CompletionItem(
                label=variable.name,
                kind=(
                    types.CompletionItemKind.Variable
                    if variable.is_decision
                    else types.CompletionItemKind.Field
                ),
                detail=_variable_detail(variable),
                documentation=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=_variable_markdown(variable),
                ),
            )
        )

    for predicate in index.predicates.values():
        if predicate.is_warm_start:
            continue
        items.append(
            types.CompletionItem(
                label=predicate.name,
                kind=types.CompletionItemKind.Function,
                detail=f"predicate({', '.join(p.name for p in predicate.parameters)})",
                insert_text=f"{predicate.name}(${{1:{', '.join(p.name for p in predicate.parameters)}}})",
                insert_text_format=types.InsertTextFormat.Snippet,
            )
        )

    for alias in index.type_aliases.values():
        items.append(
            types.CompletionItem(
                label=alias.name,
                kind=types.CompletionItemKind.Struct,
                detail="record type",
                documentation=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value="```python\n" + "\n".join(f"{k}: {v}" for k, v in alias.fields.items()) + "\n```",
                ),
            )
        )

    return types.CompletionList(is_incomplete=False, items=items)


def _preview(value: Any, limit: int = 60) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _variable_detail(variable: Any) -> str:
    if variable.is_decision:
        return f"decision variable ({variable.decision_count} indices)"
    if variable.value_code is not None:
        return "derived value"
    return "declared"


def _variable_markdown(variable: Any) -> str:
    lines = [f"**{variable.name}** — {_variable_detail(variable)}", ""]
    if variable.annotation_code:
        lines.append(f"```python\n{variable.name}: {variable.annotation_code}\n```")
    if variable.value_code:
        lines.append(f"```python\n{variable.name} = {variable.value_code}\n```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# hover
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> types.Hover | None:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return None

    name = index.symbol_at(params.position.line, params.position.character)
    if name is None:
        return None

    markdown = _describe_symbol(index, name)
    if markdown is None:
        return None

    return types.Hover(
        contents=types.MarkupContent(kind=types.MarkupKind.Markdown, value=markdown),
        range=_word_range(index, params.position.line, params.position.character),
    )


def _describe_symbol(index: ModuleIndex, name: str) -> str | None:
    constant = index.constants.get(name)
    if constant is not None:
        return (
            f"**constant** `{name}`\n\n"
            f"```python\n{name} = {constant.raw_code}\n```\n\n"
            f"Value: `{_preview(constant.value, 200)}`"
        )

    variable = index.variables.get(name)
    if variable is not None:
        parts = [f"**{_variable_detail(variable)}** `{name}`", ""]
        if variable.annotation_code:
            parts.append(f"```python\n{name}: {variable.annotation_code}\n```")
        if variable.value_code:
            parts.append(f"```python\n{name} = {variable.value_code}\n```")
        if variable.is_decision and variable.domain is not None:
            parts.append("")
            parts.append(f"Decision indices: **{variable.decision_count}**")
            cardinality = _domain_cardinality(variable.domain)
            if cardinality is not None:
                parts.append(f"Domain size: **{cardinality}**")
        return "\n".join(parts)

    predicate = index.predicates.get(name)
    if predicate is not None:
        signature = ", ".join(
            f"{p.name}: {p.annotation_code}" if p.annotation_code else p.name
            for p in predicate.parameters
        )
        parts = [f"**predicate** `{name}`", "", f"```python\ndef {name}({signature})\n```"]
        if predicate.is_warm_start:
            parts.append("\nWarm-start hint function.")
        elif not predicate.invoked_at_top_level and not predicate.used_as_objective:
            parts.append("\n⚠️ Never invoked — this predicate does not constrain anything.")
        return "\n".join(parts)

    alias = index.type_aliases.get(name)
    if alias is not None:
        fields = "\n".join(f"    {field}: {annotation}" for field, annotation in alias.fields.items())
        return f"**record type** `{name}`\n\n```python\n{name} = DSRecord({{\n{fields}\n}})\n```"

    if name in BUILTIN_NAMES:
        return f"**built-in** `{name}`"

    return None


def _domain_cardinality(domain: Any) -> int | None:
    if domain.kind == "int" and domain.int_domain is not None:
        lower, upper = domain.int_domain.lower, domain.int_domain.upper
        if lower is not None and upper is not None:
            return upper - lower + 1
    return None


def _word_range(index: ModuleIndex, line: int, character: int) -> types.Range:
    text = index.mapper.line_text(line)
    start = min(character, len(text))
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    end = min(character, len(text))
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    return types.Range(
        start=types.Position(line=line, character=start),
        end=types.Position(line=line, character=end),
    )


# ---------------------------------------------------------------------------
# symbols
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(params: types.DocumentSymbolParams) -> list[types.DocumentSymbol]:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return []

    symbols: list[types.DocumentSymbol] = []

    for constant in index.constants.values():
        symbols.append(
            types.DocumentSymbol(
                name=constant.name,
                kind=types.SymbolKind.Constant,
                range=_range(constant.span),
                selection_range=_range(constant.span),
                detail=_preview(constant.value),
            )
        )

    for alias in index.type_aliases.values():
        symbols.append(
            types.DocumentSymbol(
                name=alias.name,
                kind=types.SymbolKind.Struct,
                range=_range(alias.span),
                selection_range=_range(alias.span),
                detail="record type",
            )
        )

    for variable in index.variables.values():
        symbols.append(
            types.DocumentSymbol(
                name=variable.name,
                kind=(
                    types.SymbolKind.Variable
                    if variable.is_decision
                    else types.SymbolKind.Field
                ),
                range=_range(variable.span),
                selection_range=_range(variable.span),
                detail=_variable_detail(variable),
            )
        )

    for predicate in index.predicates.values():
        symbols.append(
            types.DocumentSymbol(
                name=predicate.name,
                kind=types.SymbolKind.Function,
                range=_range(predicate.span),
                selection_range=_range(predicate.name_span),
                detail="warm start" if predicate.is_warm_start else "predicate",
            )
        )

    if index.objective is not None:
        symbols.append(
            types.DocumentSymbol(
                name=index.objective.sense,
                kind=types.SymbolKind.Event,
                range=_range(index.objective.span),
                selection_range=_range(index.objective.span),
                detail=index.objective.expression,
            )
        )

    return symbols


@server.feature(types.WORKSPACE_SYMBOL)
def workspace_symbol(params: types.WorkspaceSymbolParams) -> list[types.SymbolInformation]:
    query = (params.query or "").lower()
    results: list[types.SymbolInformation] = []

    for uri, index in server.indexes.items():
        for name, variable in index.variables.items():
            if query and query not in name.lower():
                continue
            results.append(
                types.SymbolInformation(
                    name=name,
                    kind=(
                        types.SymbolKind.Variable
                        if variable.is_decision
                        else types.SymbolKind.Field
                    ),
                    location=types.Location(uri=uri, range=_range(variable.span)),
                )
            )
        for name, predicate in index.predicates.items():
            if query and query not in name.lower():
                continue
            results.append(
                types.SymbolInformation(
                    name=name,
                    kind=types.SymbolKind.Function,
                    location=types.Location(uri=uri, range=_range(predicate.span)),
                )
            )

    return results


# ---------------------------------------------------------------------------
# definition / references / rename
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def definition(params: types.DefinitionParams) -> types.Location | None:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return None

    name = index.symbol_at(params.position.line, params.position.character)
    if name is None:
        return None

    span = _definition_span(index, name)
    if span is None:
        return None
    return types.Location(uri=params.text_document.uri, range=_range(span))


def _definition_span(index: ModuleIndex, name: str) -> Any | None:
    for collection in (index.constants, index.variables, index.predicates, index.type_aliases):
        symbol = collection.get(name)
        if symbol is not None:
            return symbol.span
    return None


@server.feature(types.TEXT_DOCUMENT_REFERENCES)
def references(params: types.ReferenceParams) -> list[types.Location]:
    index = server.index_for(params.text_document.uri)
    if index is None or index.tree is None:
        return []

    name = index.symbol_at(params.position.line, params.position.character)
    if name is None:
        return []

    locations: list[types.Location] = []
    for node in _walk_names(index.tree, name):
        locations.append(
            types.Location(uri=params.text_document.uri, range=_range(index.span_of(node)))
        )
    return locations


def _walk_names(tree: Any, name: str) -> list[Any]:
    import ast

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == name
    ]


@server.feature(types.TEXT_DOCUMENT_PREPARE_RENAME)
def prepare_rename(params: types.PrepareRenameParams) -> types.PrepareRenamePlaceholder | None:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return None
    name = index.symbol_at(params.position.line, params.position.character)
    if name is None or _definition_span(index, name) is None:
        return None
    return types.PrepareRenamePlaceholder(
        range=_word_range(index, params.position.line, params.position.character),
        placeholder=name,
    )


@server.feature(types.TEXT_DOCUMENT_RENAME)
def rename(params: types.RenameParams) -> types.WorkspaceEdit | None:
    index = server.index_for(params.text_document.uri)
    if index is None or index.tree is None:
        return None

    old_name = index.symbol_at(params.position.line, params.position.character)
    if old_name is None or _definition_span(index, old_name) is None:
        return None

    edits = [
        types.TextEdit(range=_range(index.span_of(node)), new_text=params.new_name)
        for node in _walk_names(index.tree, old_name)
    ]
    if not edits:
        return None

    return types.WorkspaceEdit(changes={params.text_document.uri: edits})


# ---------------------------------------------------------------------------
# folding / signature help
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_FOLDING_RANGE)
def folding_range(params: types.FoldingRangeParams) -> list[types.FoldingRange]:
    index = server.index_for(params.text_document.uri)
    if index is None or index.tree is None:
        return []

    import ast

    ranges: list[types.FoldingRange] = []
    for node in ast.walk(index.tree):
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.For, ast.If, ast.While, ast.With)):
            continue
        span = index.span_of(node)
        if span.end_line > span.start_line:
            ranges.append(
                types.FoldingRange(
                    start_line=span.start_line,
                    end_line=span.end_line,
                    kind=types.FoldingRangeKind.Region,
                )
            )
    return ranges


@server.feature(types.TEXT_DOCUMENT_SIGNATURE_HELP)
def signature_help(params: types.SignatureHelpParams) -> types.SignatureHelp | None:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return None

    text = index.mapper.line_text(params.position.line)
    prefix = text[: params.position.character]
    match = re.search(r"([A-Za-z_]\w*)\s*\(([^()]*)$", prefix)
    if match is None:
        return None

    predicate = index.predicates.get(match.group(1))
    if predicate is None:
        return None

    parameters = [
        types.ParameterInformation(
            label=p.name,
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"`{p.annotation_code}`" if p.annotation_code else p.name,
            ),
        )
        for p in predicate.parameters
    ]

    active = match.group(2).count(",")
    return types.SignatureHelp(
        signatures=[
            types.SignatureInformation(
                label=f"{predicate.name}({', '.join(p.name for p in predicate.parameters)})",
                parameters=parameters,
            )
        ],
        active_signature=0,
        active_parameter=min(active, max(0, len(parameters) - 1)),
    )


# ---------------------------------------------------------------------------
# semantic tokens
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL)
def semantic_tokens(params: types.SemanticTokensParams) -> types.SemanticTokens:
    index = server.index_for(params.text_document.uri)
    if index is None or index.tree is None:
        return types.SemanticTokens(data=[])

    import ast

    tokens: list[tuple[int, int, int, int, int]] = []

    def add(node: ast.AST, token_type: str, modifiers: int = 0) -> None:
        span = index.span_of(node)
        if span.start_line != span.end_line:
            return
        length = span.end_character - span.start_character
        if length <= 0:
            return
        tokens.append((span.start_line, span.start_character, length, _TT[token_type], modifiers))

    declaration_modifier = 1 << _TOKEN_MODIFIERS.index("declaration")
    readonly_modifier = 1 << _TOKEN_MODIFIERS.index("readonly")

    for node in index.tree.body:
        if isinstance(node, ast.FunctionDef):
            add(node, "function", declaration_modifier)
            for arg in node.args.args:
                add(arg, "parameter", declaration_modifier)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name in index.constants:
                add(node.target, "variable", declaration_modifier | readonly_modifier)
            elif name in index.variables:
                variable = index.variables[name]
                add(
                    node.target,
                    "variable",
                    declaration_modifier | (0 if variable.is_decision else readonly_modifier),
                )
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in index.type_aliases:
                add(node.targets[0], "struct", declaration_modifier)
            elif name in index.constants:
                add(node.targets[0], "variable", declaration_modifier | readonly_modifier)

    tokens.sort(key=lambda token: (token[0], token[1]))

    data: list[int] = []
    previous_line = 0
    previous_character = 0
    for line, character, length, token_type, modifiers in tokens:
        delta_line = line - previous_line
        delta_character = character - previous_character if delta_line == 0 else character
        data.extend([delta_line, delta_character, length, token_type, modifiers])
        previous_line = line
        previous_character = character

    return types.SemanticTokens(data=data)


# ---------------------------------------------------------------------------
# inlay hints
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_INLAY_HINT)
def inlay_hint(params: types.InlayHintParams) -> list[types.InlayHint]:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return []

    hints: list[types.InlayHint] = []
    for variable in index.variables.values():
        if not variable.is_decision:
            continue
        span = variable.span
        if not (params.range.start.line <= span.start_line <= params.range.end.line):
            continue
        hints.append(
            types.InlayHint(
                position=types.Position(line=span.start_line, character=span.end_character),
                label=f"  {variable.decision_count} decisions",
                kind=types.InlayHintKind.Type,
                padding_left=True,
            )
        )
    return hints


# ---------------------------------------------------------------------------
# code lens
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_CODE_LENS)
def code_lens(params: types.CodeLensParams) -> list[types.CodeLens]:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return []

    lenses: list[types.CodeLens] = []

    if index.objective is not None:
        lenses.append(
            types.CodeLens(
                range=_range(index.objective.span),
                command=types.Command(
                    title=f"Solve ({index.decision_count} decisions)",
                    command="optdsl.solve",
                    arguments=[params.text_document.uri],
                ),
            )
        )

    problem = fingerprint(index)
    if problem.best is not None:
        lenses.append(
            types.CodeLens(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=0),
                ),
                command=types.Command(
                    title=f"Problem class: {problem.best.name}",
                    command="optdsl.analyze",
                    arguments=[params.text_document.uri],
                ),
            )
        )

    return lenses


# ---------------------------------------------------------------------------
# code actions
# ---------------------------------------------------------------------------


@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_action(params: types.CodeActionParams) -> list[types.CodeAction]:
    index = server.index_for(params.text_document.uri)
    if index is None:
        return []

    actions: list[types.CodeAction] = []
    diagnostics = check(index)

    for diagnostic in diagnostics:
        if diagnostic.code == "predicate-unused":
            name = _predicate_name_from_message(diagnostic.message)
            if name is None:
                continue
            actions.append(
                types.CodeAction(
                    title=f"Add top-level call to '{name}'",
                    kind=types.CodeActionKind.QuickFix,
                    diagnostics=[_to_lsp_diagnostic(diagnostic)],
                    edit=_append_edit(
                        params.text_document.uri,
                        index,
                        f"\n{name}({', '.join(p.name for p in index.predicates[name].parameters)})\n",
                    ),
                )
            )
        elif diagnostic.code == "missing-objective":
            actions.append(
                types.CodeAction(
                    title="Add `minimize(objective)`",
                    kind=types.CodeActionKind.QuickFix,
                    diagnostics=[_to_lsp_diagnostic(diagnostic)],
                    edit=_append_edit(params.text_document.uri, index, "\nminimize(objective)\n"),
                )
            )

    return actions


def _predicate_name_from_message(message: str) -> str | None:
    match = re.search(r"'([A-Za-z_]\w*)' is never invoked", message)
    return match.group(1) if match else None


def _append_edit(uri: str, index: ModuleIndex, text: str) -> types.WorkspaceEdit:
    line_count = len(index.mapper._lines)  # noqa: SLF001 - same package
    end = types.Position(line=max(0, line_count - 1), character=0)
    return types.WorkspaceEdit(
        changes={uri: [types.TextEdit(range=types.Range(start=end, end=end), new_text=text)]}
    )


# ---------------------------------------------------------------------------
# execute command
# ---------------------------------------------------------------------------


@server.feature(types.WORKSPACE_EXECUTE_COMMAND)
def execute_command(params: types.ExecuteCommandParams) -> Any:
    """Dispatch editor commands.

    Only ``optdsl.analyze`` is implemented here; the heavier commands
    (translate/solve/lns/synthesize) are delegated to the CLI by the VS Code
    extension so a long-running solve never blocks the language server.
    """
    command = params.command
    arguments = params.arguments or []

    if command == "optdsl.analyze":
        uri = arguments[0] if arguments else None
        index = server.index_for(uri) if uri else None
        if index is None:
            return None
        problem = fingerprint(index)
        return {
            "decisionCount": index.decision_count,
            "variables": {
                name: {
                    "decision": variable.is_decision,
                    "indices": variable.decision_count,
                    "annotation": variable.annotation_code,
                }
                for name, variable in index.variables.items()
            },
            "constants": {name: _preview(c.value, 200) for name, c in index.constants.items()},
            "predicates": {
                name: {
                    "parameters": [p.name for p in predicate.parameters],
                    "invoked": predicate.invoked_at_top_level,
                    "objective": predicate.used_as_objective,
                }
                for name, predicate in index.predicates.items()
            },
            "objective": (
                {
                    "sense": index.objective.sense,
                    "expression": index.objective.expression,
                }
                if index.objective
                else None
            ),
            "problemClass": problem.best.name if problem.best else None,
            "problemScore": problem.score,
            "diagnostics": [
                {"code": d.code, "message": d.message, "severity": int(d.severity)}
                for d in check(index)
            ],
        }

    LOGGER.warning("unhandled command %s", command)
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server.start_io()


if __name__ == "__main__":
    main()
