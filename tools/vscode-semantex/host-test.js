'use strict';
// Run through VS Code's --extensionTestsPath, not through node --test.
const vscode = require('vscode');
const assert = require('assert');
const fs = require('fs');
const path = require('path');

async function run() {
    const extension = vscode.extensions.getExtension('math-template.semantex-navigation');
    assert(extension, 'development extension is loaded');
    await extension.activate();
    await vscode.commands.executeCommand('semantex.refresh');
    const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
    const uri = vscode.Uri.file(path.join(root, 'draft/main.tex'));
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document);
    const position = document.positionAt(document.getText().lastIndexOf('def:base') + 3);
    const hovers = await vscode.commands.executeCommand('vscode.executeHoverProvider', uri, position);
    assert(hovers.some(h => h.contents.some(c => (c.value || String(c)).includes('Base convention'))), 'exact environment hover');
    const definitions = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', uri, position);
    assert(definitions.some(d => (d.uri || d.targetUri).fsPath === uri.fsPath), 'definition resolves in source');
    const references = await vscode.commands.executeCommand('vscode.executeReferenceProvider', uri, position);
    assert(references.length >= 1, 'reference provider returns incoming uses');
    const offset = document.getText().indexOf('Base convention');
    const edit = new vscode.WorkspaceEdit();
    edit.replace(uri, new vscode.Range(document.positionAt(offset), document.positionAt(offset + 'Base convention'.length)), 'Changed unsaved convention');
    await vscode.workspace.applyEdit(edit);
    await vscode.commands.executeCommand('semantex.refresh');
    const changed = await vscode.commands.executeCommand('vscode.executeHoverProvider', uri,
        document.positionAt(document.getText().lastIndexOf('def:base') + 3));
    assert(changed.some(h => h.contents.some(c => (c.value || String(c)).includes('Changed unsaved convention'))), 'dirty-buffer overlay used');
    assert(fs.readFileSync(uri.fsPath, 'utf8').includes('Base convention'), 'saved source remains unchanged');
    console.log('SemanTeX extension host: hover, definition, references and dirty buffers passed.');
}
module.exports = {run};
