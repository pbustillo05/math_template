'use strict';
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const {execFile} = require('child_process');

function labelAt(document, position) {
    const range = document.getWordRangeAtPosition(position, /[^\s{}\\[\],]+/);
    return range ? {label: document.getText(range), range} : undefined;
}

function inside(root, relative) {
    const target = path.resolve(root, relative);
    const rel = path.relative(root, target);
    if (path.isAbsolute(relative) || rel === '..' || rel.startsWith('..' + path.sep)) {
        throw new Error('Source target escapes the project.');
    }
    // Defend against a symlink in any source ancestor, not just lexical traversal.
    const real = fs.realpathSync(target);
    const realRel = path.relative(fs.realpathSync(root), real);
    if (realRel === '..' || realRel.startsWith('..' + path.sep) || path.isAbsolute(realRel)) {
        throw new Error('Source symlink escapes the project.');
    }
    return target;
}

class Project {
    constructor(folder, diagnostics, changed) {
        this.folder = folder;
        this.root = folder.uri.fsPath;
        this.diagnostics = diagnostics;
        this.changed = changed;
        this.nodes = new Map();
        this.references = [];
        this.generation = 0;
        this.pending = null;
    }
    schedule() {
        clearTimeout(this.timer);
        this.timer = setTimeout(() => this.refresh(), 350);
    }
    async refresh() {
        if (!vscode.workspace.isTrusted) return;
        const generation = ++this.generation;
        const output = path.join(this.root, 'build/semantex');
        fs.mkdirSync(output, {recursive: true});
        const overlayPath = path.join(output, `editor-overlays-${process.pid}-${generation}.json`);
        const overlays = {};
        for (const doc of vscode.workspace.textDocuments) {
            if (!doc.isDirty || doc.uri.scheme !== 'file' || !doc.uri.fsPath.endsWith('.tex')) continue;
            const rel = path.relative(this.root, doc.uri.fsPath).split(path.sep).join('/');
            if (/^(draft|notes|references)\//.test(rel)) overlays[rel] = doc.getText();
        }
        fs.writeFileSync(overlayPath, JSON.stringify(overlays));
        const python = vscode.workspace.getConfiguration('semantex', this.folder.uri).get('pythonPath', 'python3');
        this.pending = new Promise(resolve => {
            execFile(python, ['-B', path.join(this.root, 'scripts/manuscript_graph.py'), '--root', this.root,
                '--overlays', overlayPath, 'editor-index'], {cwd: this.root, maxBuffer: 64 * 1024 * 1024, timeout: 30000},
            (error, stdout, stderr) => {
                try {
                    if (generation !== this.generation) return;
                    const data = error ? {nodes: [], references: [], errors: [stderr || error.message]} : JSON.parse(stdout);
                    this.nodes = new Map(data.nodes.map(n => [n.id, n]));
                    this.references = data.references;
                    const grouped = new Map();
                    for (const message of data.errors || []) {
                        const match = /^(.*?\.tex):(\d+)(?::(\d+))?:?\s*(.*)$/.exec(message);
                        const file = match ? match[1] : 'draft/main.tex';
                        const uri = vscode.Uri.file(inside(this.root, file));
                        const line = match ? Math.max(0, Number(match[2]) - 1) : 0;
                        const diagnostic = new vscode.Diagnostic(new vscode.Range(line, 0, line, 1),
                            match ? match[4] : message, vscode.DiagnosticSeverity.Error);
                        const key = uri.toString();
                        if (!grouped.has(key)) grouped.set(key, [uri, []]);
                        grouped.get(key)[1].push(diagnostic);
                    }
                    this.diagnostics.set(Array.from(grouped.values()));
                    // Clear this project's old diagnostics without affecting other folders.
                    for (const [uri] of this.diagnostics) {
                        const rel = path.relative(this.root, uri.fsPath);
                        if (!rel.startsWith('..') && !grouped.has(uri.toString())) this.diagnostics.delete(uri);
                    }
                    this.changed();
                } catch (failure) {
                    this.nodes.clear();
                    this.references = [];
                    void vscode.window.showWarningMessage('SemanTeX index: ' + failure.message);
                } finally {
                    try { fs.unlinkSync(overlayPath); } catch (_) { /* Already cleaned. */ }
                    resolve();
                }
            });
        });
        return this.pending;
    }
    async ready() { if (this.pending) await this.pending; }
    dispose() { clearTimeout(this.timer); this.generation++; }
}

function activate(context) {
    const diagnostics = vscode.languages.createDiagnosticCollection('semantex');
    const emitter = new vscode.EventEmitter();
    const projects = new Map();
    let selected;
    const discover = () => {
        for (const folder of vscode.workspace.workspaceFolders || []) {
            if (folder.uri.scheme !== 'file' || !fs.existsSync(path.join(folder.uri.fsPath, 'scripts/semantex'))) continue;
            if (!projects.has(folder.uri.toString())) {
                const project = new Project(folder, diagnostics, () => emitter.fire());
                projects.set(folder.uri.toString(), project);
                void project.refresh();
            }
        }
        for (const [key, project] of projects) {
            if (!(vscode.workspace.workspaceFolders || []).some(f => f.uri.toString() === key)) {
                project.dispose(); projects.delete(key);
            }
        }
    };
    const projectFor = uri => {
        const folder = vscode.workspace.getWorkspaceFolder(uri);
        return folder ? projects.get(folder.uri.toString()) : undefined;
    };
    const lookup = async (doc, pos) => {
        const project = projectFor(doc.uri);
        if (!project) return undefined;
        await project.ready();
        const token = labelAt(doc, pos);
        const node = token && project.nodes.get(token.label);
        return node ? {project, token, node} : undefined;
    };
    const selector = [{language: 'latex', scheme: 'file'}, {language: 'tex', scheme: 'file'}];
    context.subscriptions.push(diagnostics, emitter,
        vscode.workspace.onDidChangeWorkspaceFolders(discover),
        vscode.workspace.onDidChangeTextDocument(e => projectFor(e.document.uri)?.schedule()),
        vscode.workspace.onDidSaveTextDocument(doc => projectFor(doc.uri)?.schedule()),
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('semantex.pythonPath')) for (const p of projects.values()) void p.refresh();
        }),
        vscode.languages.registerHoverProvider(selector, {async provideHover(doc, pos) {
            const found = await lookup(doc, pos);
            if (!found) return undefined;
            const {node, token} = found;
            const md = new vscode.MarkdownString();
            md.appendText(`${node.id} · ${node.status || 'unreviewed'}${node.virtual ? ' · virtual source label' : ''}\n\n`);
            md.appendText(`Prerequisites: ${(node.dependencies || []).join(', ') || 'none declared'}\n\n`);
            for (const block of node.blocks || []) {
                md.appendText(`${block.file}:${block.start_line}–${block.end_line}\n\n`);
                // Bound hover size; exact full blocks remain available through the CLI.
                md.appendCodeblock(block.latex.slice(0, 16000) + (block.latex.length > 16000 ? '\n% … use the CLI for the full unit' : ''), 'latex');
            }
            return new vscode.Hover(md, token.range);
        }}),
        vscode.languages.registerDefinitionProvider(selector, {async provideDefinition(doc, pos) {
            const found = await lookup(doc, pos);
            if (!found) return undefined;
            return new vscode.Location(vscode.Uri.file(inside(found.project.root, found.node.file)),
                new vscode.Position(found.node.line - 1, Math.max(0, (found.node.column || 1) - 1)));
        }}),
        vscode.languages.registerReferenceProvider(selector, {async provideReferences(doc, pos, options) {
            const found = await lookup(doc, pos);
            if (!found) return [];
            const result = found.project.references.filter(r => r.target === found.node.id).map(r =>
                new vscode.Location(vscode.Uri.file(inside(found.project.root, r.file)),
                    new vscode.Position(r.line - 1, Math.max(0, (r.column || 1) - 1))));
            if (options.includeDeclaration) result.push(new vscode.Location(vscode.Uri.file(inside(found.project.root, found.node.file)),
                new vscode.Position(found.node.line - 1, 0)));
            return result;
        }}),
        vscode.commands.registerCommand('semantex.refresh', () => Promise.all(Array.from(projects.values(), p => p.refresh()))),
        vscode.commands.registerCommand('semantex.showDependencies', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const found = await lookup(editor.document, editor.selection.active);
            if (!found) { void vscode.window.showInformationMessage('Place the cursor on an indexed label first.'); return; }
            selected = {project: found.project, id: found.node.id, trail: []};
            emitter.fire();
            await vscode.commands.executeCommand('semantex.dependencies.focus');
        }),
        vscode.commands.registerCommand('semantex.openUnit', async item => {
            const node = item.project.nodes.get(item.id);
            if (!node) return;
            await vscode.window.showTextDocument(vscode.Uri.file(inside(item.project.root, node.file)),
                {selection: new vscode.Range(node.line - 1, 0, node.line - 1, 0)});
        }),
        vscode.window.registerTreeDataProvider('semantex.dependencies', {
            onDidChangeTreeData: emitter.event,
            getTreeItem(item) {
                const node = item.project.nodes.get(item.id);
                const cycle = item.trail.includes(item.id);
                const children = node?.dependencies || [];
                const tree = new vscode.TreeItem(item.id, children.length && !cycle ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
                tree.description = cycle ? 'repeat' : node?.status;
                tree.tooltip = `${item.project.folder.name}: arrows lead to declared prerequisites`;
                tree.command = {command: 'semantex.openUnit', title: 'Open unit', arguments: [item]};
                return tree;
            },
            getChildren(item) {
                if (!item) {
                    if (selected && selected.project.nodes.has(selected.id)) return [selected];
                    return Array.from(projects.values()).flatMap(project => Array.from(project.nodes.values())
                        .filter(n => n.kind !== 'external' && n.kind !== 'prf' && n.dependencies?.length)
                        .map(n => ({project, id: n.id, trail: []})));
                }
                if (item.trail.includes(item.id)) return [];
                return (item.project.nodes.get(item.id)?.dependencies || []).filter(id => item.project.nodes.has(id))
                    .map(id => ({project: item.project, id, trail: item.trail.concat(item.id)}));
            }
        }),
        {dispose: () => { for (const p of projects.values()) p.dispose(); }});
    discover();
}

module.exports = {activate, labelAt, inside};
