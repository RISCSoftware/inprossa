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
exports.listModels = listModels;
exports.resolveModel = resolveModel;
exports.selectModelCommand = selectModelCommand;
exports.complete = complete;
exports.describeModelError = describeModelError;
const vscode = __importStar(require("vscode"));
/**
 * Model selection for the AI features.
 *
 * Deliberately does NOT filter on `vendor: 'copilot'`. `vscode.lm.selectChatModels`
 * returns every model the user has made available to extensions, which includes
 * BYOK providers (OpenAI, Anthropic, Azure, Gemini, Ollama, OpenRouter, ...).
 * Hardcoding a vendor would silently exclude those users.
 */
const MODEL_SETTING = 'optdsl.languageModel';
async function listModels() {
    const models = await vscode.lm.selectChatModels({});
    return models
        .map((model) => ({
        model,
        label: `${model.name} — ${model.vendor}/${model.family} (${Math.round(model.maxInputTokens / 1000)}k ctx)`,
    }))
        .sort((a, b) => a.label.localeCompare(b.label));
}
/**
 * Resolve the model to use, honouring the `optdsl.languageModel` setting.
 *
 * Returns `undefined` when no model is available, so callers can show a clear
 * message instead of throwing.
 */
async function resolveModel() {
    const configured = vscode.workspace.getConfiguration().get(MODEL_SETTING, '').trim();
    const choices = await listModels();
    if (choices.length === 0) {
        return undefined;
    }
    if (configured) {
        const match = choices.find((choice) => choice.model.id === configured || choice.model.name === configured);
        if (match) {
            return match.model;
        }
        // The configured model is gone (uninstalled provider, revoked access).
        // Fall through to the picker rather than failing silently.
    }
    if (choices.length === 1) {
        return choices[0].model;
    }
    const picked = await vscode.window.showQuickPick(choices.map((choice) => ({ label: choice.label, model: choice.model })), { title: 'Select a language model for OptDSL', placeHolder: 'Models from all configured providers' });
    if (!picked) {
        return undefined;
    }
    await vscode.workspace
        .getConfiguration()
        .update(MODEL_SETTING, picked.model.id, vscode.ConfigurationTarget.Global);
    return picked.model;
}
async function selectModelCommand() {
    const choices = await listModels();
    if (choices.length === 0) {
        void vscode.window.showWarningMessage('No language models are available. Sign in to GitHub Copilot or configure a provider in VS Code.');
        return;
    }
    const picked = await vscode.window.showQuickPick(choices.map((choice) => ({ label: choice.label, model: choice.model })), { title: 'Select a language model for OptDSL' });
    if (!picked) {
        return;
    }
    await vscode.workspace
        .getConfiguration()
        .update(MODEL_SETTING, picked.model.id, vscode.ConfigurationTarget.Global);
    void vscode.window.showInformationMessage(`OptDSL will use ${picked.model.name}.`);
}
/**
 * Send a prompt and collect the full response.
 *
 * The LM API streams fragments; for structured output (JSON, a Python class) we
 * need the whole thing before parsing, so this buffers.
 */
async function complete(model, messages, token) {
    const response = await model.sendRequest(messages, {}, token);
    let text = '';
    for await (const fragment of response.text) {
        text += fragment;
    }
    return text;
}
/**
 * Turn an LM error into a message a user can act on.
 */
function describeModelError(error) {
    if (error instanceof vscode.LanguageModelError) {
        switch (error.code) {
            case 'NoPermissions':
                return 'OptDSL is not allowed to use this model. Grant access when prompted, or pick another model.';
            case 'Blocked':
                return 'The request was blocked by the model provider.';
            case 'NotFound':
                return 'The selected model is no longer available. Run "OptDSL: Select Language Model".';
            default:
                return `Language model error (${error.code}): ${error.message}`;
        }
    }
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
}
//# sourceMappingURL=model.js.map