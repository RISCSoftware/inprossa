"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const node_1 = require("vscode-languageclient/node");
const constraints_1 = require("./constraints");
const model_1 = require("./model");
const operators_1 = require("./operators");
const python_1 = require("./python");
let client;
async function activate(context) {
    const output = vscode.window.createOutputChannel('OptDSL');
    context.subscriptions.push(output);
    output.appendLine(`OptDSL activating (extension ${context.extension.packageJSON.version})`);
    // Anchor path resolution to the extension's own location. An Extension
    // Development Host opened with only --extensionDevelopmentPath has no
    // workspace folder, so workspaceFolders/process.cwd() are both wrong.
    (0, python_1.configure)(context.extensionPath);
    output.appendLine(`extension path: ${context.extensionPath}`);
    // Register commands FIRST. If the language client throws during
    // construction, the commands must still work — they shell out to Python
    // directly and do not need the server.
    const register = (id, handler) => context.subscriptions.push(vscode.commands.registerCommand(id, handler));
    register('optdsl.addConstraint', constraints_1.addConstraintCommand);
    register('optdsl.explainModel', operators_1.explainModelCommand);
    register('optdsl.synthesizeOperator', operators_1.synthesizeOperatorCommand);
    register('optdsl.showAnalysis', operators_1.showAnalysisCommand);
    register('optdsl.selectModel', model_1.selectModelCommand);
    register('optdsl.solve', operators_1.solveCommand);
    register('optdsl.runLns', operators_1.runLnsCommand);
    try {
        client = createClient();
        context.subscriptions.push(client);
        // Do not await: a slow or failing server must not block activation.
        client.start().catch((error) => {
            const message = error instanceof Error ? error.message : String(error);
            output.appendLine(`language server failed to start: ${message}`);
            void vscode.window.showErrorMessage(`OptDSL: the language server failed to start. ${message}`);
        });
    }
    catch (error) {
        // A throw here would abort activation and make the extension look dead.
        const message = error instanceof Error ? error.message : String(error);
        output.appendLine(`language client construction failed: ${message}`);
        void vscode.window.showErrorMessage(`OptDSL: ${message}`);
    }
    output.appendLine('OptDSL activated');
}
async function deactivate() {
    if (client) {
        await client.stop();
        client = undefined;
    }
}
function createClient() {
    const config = vscode.workspace.getConfiguration('optdsl');
    // Use the same resolution as the bridge: the venv interpreter and the
    // extension-anchored repo root. Duplicating this logic here is what let the
    // server and the bridge disagree about which Python to run.
    const python = (0, python_1.resolvePythonPath)();
    const repoRoot = (0, python_1.resolveRepoRoot)();
    const serverOptions = {
        command: python,
        args: ['-m', 'optdsl_lsp', ...config.get('serverArgs', [])],
        options: {
            cwd: repoRoot,
            env: {
                ...process.env,
                PYTHONPATH: [
                    repoRoot,
                    path.join(repoRoot, 'optdsl-lsp'),
                    path.join(repoRoot, 'operator-synthesis'),
                    process.env.PYTHONPATH ?? '',
                ]
                    .filter(Boolean)
                    .join(path.delimiter),
                PYTHONIOENCODING: 'utf-8',
            },
        },
        transport: node_1.TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'optdsl' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.dsl'),
        },
        outputChannelName: 'OptDSL',
    };
    return new node_1.LanguageClient('optdsl', 'OptDSL Language Server', serverOptions, clientOptions);
}
//# sourceMappingURL=extension.js.map