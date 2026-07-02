# TypeScript Conventions

Opinionated standards for TypeScript 5.x+. Assumes JavaScript basics this covers the type system and TS-specific decisions.
Based on [TypeScript Documentation](https://www.typescriptlang.org/docs/), [TypeScript Performance Wiki](https://github.com/microsoft/TypeScript/wiki/Performance), and [typescript-eslint](https://typescript-eslint.io/).

## Tooling

> Ref: [TSConfig Reference](https://www.typescriptlang.org/tsconfig/), [typescript-eslint](https://typescript-eslint.io/getting-started)

- **Type checker**: `tsc` with `strict: true` no exceptions
- **Linter**: ESLint with `typescript-eslint` (flat config)
- **Build**: `tsc` for libraries, Vite/esbuild for applications
- **tsconfig base**: extend from `@tsconfig/strictest` or `@tsconfig/node22`

## tsconfig Essentials

> Ref: [Strict mode](https://www.typescriptlang.org/tsconfig/#strict), [Module Resolution](https://www.typescriptlang.org/docs/handbook/modules/theory.html)

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "moduleResolution": "bundler",
    "module": "ESNext",
    "target": "ES2022"
  }
}
```

- `noUncheckedIndexedAccess`: catches `array[i]` returning `T | undefined` handle the undefined case
- `exactOptionalPropertyTypes`: `{ a?: string }` means `a` is `string | undefined`, not that `a` can be explicitly set to `undefined`
- `moduleResolution: "bundler"`: correct for Vite/esbuild projects; use `"node16"` for Node ESM packages

## Type System Patterns

> Ref: [TypeScript Handbook Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html), [Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)

### Prefer `type` over `interface` for most cases

```ts
// type composable, supports unions/intersections
type User = { id: string; name: string };
type Admin = User & { permissions: string[] };

// interface use when you need declaration merging (rare: module augmentation)
interface Window {
  myLib: MyLib;
}
```

### Discriminated unions over optional fields

```ts
// Bad optional fields create ambiguity
type Result = { data?: User; error?: string };

// Good exhaustively checkable
type Result = { status: 'ok'; data: User } | { status: 'error'; message: string };
```

### Utility types

```ts
Partial<T>; // all fields optional
Required<T>; // all fields required
Readonly<T>; // immutable
Pick<T, K>; // subset of fields
Omit<T, K>; // exclude fields
Record<K, V>; // typed object map
ReturnType<F>; // infer function return
Parameters<F>; // infer function parameters
NonNullable<T>; // remove null/undefined
```

### Template literal types for string patterns

```ts
type EventName = `on${Capitalize<string>}`;
type CssUnit = `${number}px` | `${number}em` | `${number}%`;
```

### `satisfies` for type-checking without widening

```ts
// satisfies checks the type but keeps the literal type
const config = {
  port: 3000,
  host: 'localhost',
} satisfies ServerConfig; // errors if fields missing, but port stays `3000` not `number`
```

## Generic Constraints

> Ref: [Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html)

```ts
// Constrain to objects with a specific shape
function getField<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Default type parameters (TS 5.0+)
type Container<T = string> = { value: T };
```

## `unknown` vs `any`

> Ref: [unknown type](https://www.typescriptlang.org/docs/handbook/2/functions.html#unknown), [Type Guards](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#using-type-predicates)

- `unknown` is the safe top type requires narrowing before use
- `any` disables type checking entirely never use in new code
- Use `unknown` for: catch clause variables, external API responses, dynamic data

```ts
function parseJson(raw: string): unknown {
  return JSON.parse(raw);
}

// Type guard for narrowing
function isUser(val: unknown): val is User {
  return typeof val === 'object' && val !== null && 'id' in val;
}
```

## Enums Avoid, Use `const` Objects

```ts
// Avoid TypeScript enum has runtime behavior, compiles to IIFE
enum Direction {
  Up,
  Down,
}

// Prefer const object + union type
const Direction = { Up: 'up', Down: 'down' } as const;
type Direction = (typeof Direction)[keyof typeof Direction];
// Direction = 'up' | 'down'
```

## Module Augmentation

```ts
// Extending third-party types (e.g., Express Request)
declare module 'express-serve-static-core' {
  interface Request {
    user?: AuthUser;
  }
}
```

## Anti-Patterns to Flag

- `as` casts without type guards tells the compiler to trust you, but if you're wrong the error surfaces at runtime, not compile time; use type guards or `satisfies` instead
- `!` non-null assertions on user-facing data hides null/undefined bugs; handle the null case explicitly with narrowing
- `any` in function signatures disables type checking for everything downstream; use `unknown` + narrowing to maintain safety
- `interface` for everything use `type` for unions, intersections, and most definitions; `interface` only when declaration merging is needed (module augmentation)
- `namespace` declarations legacy TS pattern; use ES module `import`/`export` instead
- Re-exporting `*` without explicit names breaks tree-shaking, creates ambiguous exports, and makes the public API surface invisible
- Circular imports causes `undefined` at runtime depending on evaluation order; restructure to a shared module
- Overusing `enum` TypeScript enums generate runtime code and an IIFE; prefer `as const` objects + union types for zero-runtime alternatives
- `// @ts-ignore` without specific error suppression use `// @ts-expect-error` which fails when the error is fixed, preventing stale suppressions

## Self-Check

- [ ] `strict: true` in tsconfig non-negotiable
- [ ] `noUncheckedIndexedAccess: true` enabled
- [ ] No `any` in function signatures `unknown` + narrowing used instead
- [ ] Discriminated unions used instead of optional fields for variant types
- [ ] `satisfies` used to validate types without widening
- [ ] No `as` casts without preceding type guard or validation
- [ ] `const` objects + union types instead of `enum`
- [ ] `// @ts-expect-error` over `// @ts-ignore`
- [ ] `typescript-eslint` configured and passing in CI
- [ ] No circular imports between modules
