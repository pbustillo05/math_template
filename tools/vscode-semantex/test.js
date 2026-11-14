'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const original = Module._load;
Module._load = function(name, ...args) { return name === 'vscode' ? {} : original.call(this, name, ...args); };
const {inside, labelAt} = require('./extension');
Module._load = original;

test('source navigation rejects traversal and symlink escapes', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'semantex-test-'));
    try {
        const root = path.join(temp, 'project'); fs.mkdirSync(root);
        fs.writeFileSync(path.join(root, 'unit.tex'), 'test');
        fs.writeFileSync(path.join(temp, 'outside.tex'), 'private');
        assert.equal(inside(root, 'unit.tex'), path.join(root, 'unit.tex'));
        assert.throws(() => inside(root, '../outside.tex'), /escapes/);
        fs.symlinkSync(path.join(temp, 'outside.tex'), path.join(root, 'link.tex'));
        assert.throws(() => inside(root, 'link.tex'), /escapes/);
    } finally { fs.rmSync(temp, {recursive: true, force: true}); }
});

test('label token recognizes namespaced alpha keys and virtual environment IDs', () => {
    for (const label of ['lem:image-fixed', 'ABC+24:thm:one', 'P:auto:0123:lemma:2']) {
        const document = {getWordRangeAtPosition(position, regex) {
            assert.equal(regex.exec(label)[0], label); return {label};
        }, getText(range) { return range.label; }};
        assert.equal(labelAt(document, {}).label, label);
    }
});
