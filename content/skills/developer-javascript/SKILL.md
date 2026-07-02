# JavaScript Conventions

Modern JavaScript (ES2022+) standards. This skill covers non-obvious choices basic syntax is assumed known.
Based on [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/JavaScript), [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices), and [TC39 Proposals](https://github.com/tc39/proposals).

## Tooling

> Ref: [Vite](https://vite.dev/guide/), [ESLint Flat Config](https://eslint.org/docs/latest/use/configure/configuration-files)

- **Bundler**: Vite (browser/library), esbuild (Node CLI tools), Rollup (pure libraries)
- **Linter**: ESLint with `@eslint/js` flat config (`eslint.config.js`)
- **Formatter**: Prettier (separate from linting don't configure style rules in ESLint)
- **Package manager**: pnpm (preferred), npm as fallback
- **Node version**: `.nvmrc` or `engines` field in `package.json`

## Module System

> Ref: [MDN JavaScript Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules), [Node.js ESM](https://nodejs.org/api/esm.html)

Always use **ESM** (`import`/`export`) in new code. CommonJS only when targeting old Node APIs or legacy consumers.

```js
// Good named exports, explicit paths
export function parseConfig(raw) { ... }
export { parseConfig, validateConfig }

// Avoid default exports for non-singleton modules (hard to rename/tree-shake)
export default { parseConfig }
```

Use `import.meta.url` for `__dirname` equivalent in ESM:

```js
import { fileURLToPath } from 'node:url';
const __dirname = fileURLToPath(new URL('.', import.meta.url));
```

## Async Patterns

> Ref: [MDN Using Promises](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises), [AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)

- Use `async/await` over raw Promises in application code
- Use `Promise.all` / `Promise.allSettled` for parallel operations never `await` in a loop when operations are independent
- Prefer `Promise.allSettled` when partial failures are acceptable

```js
// Good parallel
const [users, posts] = await Promise.all([fetchUsers(), fetchPosts()]);

// Bad sequential when not needed
const users = await fetchUsers();
const posts = await fetchPosts();
```

- Use `AbortController` for cancellable fetch/async operations
- Wrap `async` event handlers in error boundaries unhandled rejections in event listeners don't propagate

## Error Handling

> Ref: [MDN Error](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error), [Error cause](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/cause)

- Use `instanceof` checks, not `.name` string comparisons
- Create typed error classes for domain errors:

```js
class ValidationError extends Error {
  constructor(field, message) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}
```

- Never swallow errors silently: `catch (e) {}` is always wrong
- Use `cause` chaining for wrapping errors: `new Error('DB failed', { cause: e })`

## DOM and Browser

- Prefer `addEventListener` over inline handlers
- Use `dataset` for element state over custom attributes
- Use `element.closest()` for event delegation don't query the full document inside handlers
- Use `IntersectionObserver` / `ResizeObserver` over scroll/resize event listeners
- Avoid `document.write()` and `innerHTML` with untrusted content (XSS)

## Node.js Conventions

> Ref: [Node.js API](https://nodejs.org/api/), [node: imports](https://nodejs.org/api/esm.html#node-imports)

- Prefer `node:` prefix for built-ins: `import fs from 'node:fs/promises'`
- Use `fs/promises` over callback-based `fs`
- Use `process.env` for config validate presence at startup, not at usage
- Structure CLI tools with a `bin/` entry point separate from library logic

## Patterns to Prefer

| Prefer                    | Over                                         |
| ------------------------- | -------------------------------------------- | --- | ------------------------------------------------ |
| `Array.from(nodeList)`    | `[...nodeList]` (creates intermediate array) |
| `structuredClone(obj)`    | `JSON.parse(JSON.stringify(obj))`            |
| `Object.hasOwn(obj, key)` | `obj.hasOwnProperty(key)`                    |
| `at(-1)` for last element | `arr[arr.length - 1]`                        |
| `crypto.randomUUID()`     | External UUID libraries                      |
| Nullish coalescing `??`   | `                                            |     | ` for default values (avoids false/0 edge cases) |
| Optional chaining `?.`    | Nested `&&` guards                           |

## Anti-Patterns to Flag

- `var` declarations function-scoped, hoisted, causes subtle bugs; always use `const`, use `let` only when reassignment is needed
- `==` comparisons type coercion leads to surprising behavior (`"" == 0` is true); always use `===`
- Mutating function arguments side effects make code unpredictable; return new values instead
- Callback hell deeply nested callbacks are unreadable; use async/await or Promise chains
- `for...in` on arrays iterates over all enumerable properties including inherited ones; use `for...of` or array methods
- Wildcard re-exports `export * from './module'` breaks tree-shaking, causes ambiguous name conflicts, and hides the public API surface
- `eval()` or `Function()` constructor executes arbitrary code, XSS vector, no static analysis possible
- Synchronous operations in event loop (`fs.readFileSync` in hot paths) blocks the entire process; use async equivalents
- `await` in loops when operations are independent runs sequentially instead of in parallel; use `Promise.all`
- Swallowing errors with empty `catch (e) {}` hides bugs; always log, rethrow, or handle explicitly

## Testing

> Ref: [Vitest](https://vitest.dev/guide/), [Node.js Test Runner](https://nodejs.org/api/test.html)

- Framework: **Vitest** (browser + Node), Jest as fallback
- Name tests: `describe('module') > it('does X when Y')`
- Use `vi.fn()` / `vi.spyOn()` for mocks, clean up with `vi.restoreAllMocks()`
- Test observable behavior, not internal implementation details

## Self-Check

- [ ] ESM everywhere no `require()` in new code
- [ ] `const` by default, `let` only when reassigned, no `var`
- [ ] `===` for all comparisons
- [ ] Parallel async operations use `Promise.all` / `Promise.allSettled`
- [ ] Error classes use `cause` chaining for wrapping
- [ ] No empty `catch` blocks errors are logged or rethrown
- [ ] Node.js built-ins use `node:` prefix (`import fs from 'node:fs/promises'`)
- [ ] Environment variables validated at startup, not at usage
- [ ] No `eval()`, `Function()`, or `innerHTML` with untrusted content
- [ ] ESLint + Prettier configured and passing in CI
