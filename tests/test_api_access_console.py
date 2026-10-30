"""Exercise the API 接入 console page with a small Node DOM shim."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from src import main

_API_FUNCTIONS = (
    "apiBaseValue",
    "apiKeyValue",
    "apiFieldText",
    "fillApiPlaceholders",
    "copyText",
    "copyApiField",
    "toggleApiKey",
    "copyApiKey",
    "copyApiSnippet",
)

_API_PAGE_TOKENS = (
    'data-page="api-info"',
    'data-tab="api-info"',
    'id="api-base"',
    "/v1/chat/completions",
    "/v1/messages",
    "/v1/responses",
    "ANTHROPIC_BASE_URL",
)


def _api_page_source() -> str:
    html = main._web_login_html()
    script = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)[-1]
    chunks = []
    for name in _API_FUNCTIONS:
        marker = f"function {name}("
        start = script.index(marker)
        opening = script.index("{", start)
        depth = 0
        for index in range(opening, len(script)):
            char = script[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    chunks.append(script[start : index + 1])
                    break
        else:  # pragma: no cover - generated console is unterminated
            raise AssertionError(f"unterminated generated function: {name}")
    return "\n".join(chunks)


@pytest.mark.parametrize("token", _API_PAGE_TOKENS)
def test_api_page_renders_keys_and_endpoints(token):
    assert token in main._web_login_html()


def test_api_page_javascript_fills_placeholders_and_masks_keys():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is not installed for console JavaScript verification")

    source = _api_page_source()
    javascript = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');

const SOURCE = __SOURCE__;
const ORIGIN = 'http://relay.example:8123';

class Element {
  constructor(id = '') {
    this.id = id;
    this._text = '';
    this._attrs = new Map();
  }
  get textContent() { return this._text; }
  set textContent(value) { this._text = String(value); }
  getAttribute(name) { return this._attrs.has(name) ? this._attrs.get(name) : null; }
  setAttribute(name, value) { this._attrs.set(name, String(value)); }
  hasAttribute(name) { return this._attrs.has(name); }
}

const base = new Element('api-base');
base.textContent = '__API_BASE__';
base.setAttribute('data-api-base', '');

const endpoints = [new Element('e1'), new Element('e2')];
endpoints[0].textContent = '__API_BASE__/v1/chat/completions';
endpoints[0].setAttribute('data-api-base', '');
endpoints[1].textContent = '__API_BASE__/v1/messages';
endpoints[1].setAttribute('data-api-base', '');

const snippet = new Element('s1');
snippet.textContent =
  'export ANTHROPIC_BASE_URL=__API_BASE__\nexport ANTHROPIC_API_KEY=__API_KEY__';

const key = new Element('api-key-1');
key.setAttribute('data-full', 'sk-local-secret');
key.setAttribute('data-masked', 'sk-l********cret');
key.textContent = 'sk-l********cret';

const elements = new Map([
  ['api-base', base],
  ['api-key-1', key],
  ['api-info-msg', new Element('api-info-msg')]
]);
const messages = [];

const context = {
  window: {location: {origin: ORIGIN}},
  navigator: {},
  helperEndpointPath: () => '',
  document: {
    getElementById: id => elements.get(id) || null,
    querySelector: selector => (selector === '.api-value[data-full]' ? key : null),
    querySelectorAll: selector => {
      if (selector === '[data-api-base]') return [base, ...endpoints];
      if (selector === '.api-snippet-body') return [snippet];
      return [];
    }
  },
  showMsg: (id, text, ok) => messages.push({id, text, ok})
};
vm.createContext(context);
new vm.Script(SOURCE).runInContext(context);
context.fillApiPlaceholders();

// Base URL follows the live browser origin, not a stale server value.
assert.equal(base.textContent, ORIGIN);
assert.equal(endpoints[0].textContent, ORIGIN + '/v1/chat/completions');
assert.equal(endpoints[1].textContent, ORIGIN + '/v1/messages');
assert.equal(
  snippet.textContent,
  'export ANTHROPIC_BASE_URL=' + ORIGIN +
  '\nexport ANTHROPIC_API_KEY=sk-local-secret'
);

// Filling twice must not double-apply the substitution.
context.fillApiPlaceholders();
assert.equal(endpoints[0].textContent, ORIGIN + '/v1/chat/completions');

// The key starts masked and toggles to the full value and back.
assert.equal(key.textContent, 'sk-l********cret');
context.toggleApiKey('api-key-1');
assert.equal(key.textContent, 'sk-local-secret');
context.toggleApiKey('api-key-1');
assert.equal(key.textContent, 'sk-l********cret');

// Copy helpers report through the page message slot.
context.copyApiKey('api-key-1');
assert.ok(messages.length > 0);
""".replace("__SOURCE__", json.dumps(source, ensure_ascii=False))

    result = subprocess.run(
        [node, "-e", javascript],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout
