# Astro Framework Conventions

Standards for building with Astro (v4/v5). Covers the patterns that differ from generic web frameworks.
Based on [Astro Documentation](https://docs.astro.build/) and [Astro Integration Guide](https://docs.astro.build/en/guides/integrations-guide/).

## Core Mental Model

> Ref: [Why Astro Islands Architecture](https://docs.astro.build/en/concepts/islands/)

Astro defaults to **zero JavaScript sent to the browser**. Every component renders server-side to HTML. Interactive components ("islands") opt in to client-side JS explicitly with a `client:*` directive.

```
Static by default → opt-in to interactivity
Server renders everything → ship only what needs to be interactive
```

## Project Structure

> Ref: [Project Structure](https://docs.astro.build/en/basics/project-structure/)

```
src/
├── pages/          # File-based routing every .astro/.md here = a route
├── layouts/        # Shared page shells (BaseLayout, BlogLayout, etc.)
├── components/     # UI components (.astro + framework components)
├── content/        # Content collections (type-safe markdown/MDX/JSON)
├── styles/         # Global CSS, base styles
└── lib/ or utils/  # Shared helpers, non-component logic
public/             # Static assets (copied verbatim, no processing)
astro.config.mjs    # Config integrations, output, adapter
```

## Components

> Ref: [Astro Components](https://docs.astro.build/en/basics/astro-components/)

Astro components (`.astro`) use a two-section syntax: a frontmatter script block and an HTML template.

```astro
---
// Frontmatter: runs server-side only
import { getCollection } from 'astro:content'
import Layout from '../layouts/BaseLayout.astro'

const { title } = Astro.props
const posts = await getCollection('blog')
---

<!-- Template: renders to HTML -->
<Layout title={title}>
  {posts.map(post => <article>{post.data.title}</article>)}
</Layout>
```

**Key rules:**

- Frontmatter runs once at build time (SSG) or per request (SSR) never in the browser
- No `useState`, `useEffect` those belong in framework components (React/Vue/etc.)
- Use `Astro.props` for component inputs, `Astro.slots` for slots

## Islands Architecture

> Ref: [Astro Islands](https://docs.astro.build/en/concepts/islands/), [Client Directives](https://docs.astro.build/en/reference/directives-reference/#client-directives)

Client-side interactivity requires a `client:*` directive on a framework component:

```astro
---
import SearchBar from './SearchBar.jsx'  // React component
import Counter from './Counter.svelte'   // Svelte component
---

<!-- Load immediately when page loads -->
<SearchBar client:load />

<!-- Load when component enters viewport -->
<Counter client:visible />

<!-- Load after page is interactive (non-critical) -->
<Newsletter client:idle />

<!-- Never send JS (static render only) -->
<HeavyChart client:only="react" />
```

**Rule**: Only add `client:*` when the component genuinely needs browser interactivity. Most UI is server-rendered.

## Content Collections

> Ref: [Content Collections](https://docs.astro.build/en/guides/content-collections/)

Type-safe structured content using schemas. Define once in `src/content/config.ts`:

```ts
import { defineCollection, z } from 'astro:content';

export const collections = {
  blog: defineCollection({
    type: 'content', // markdown/MDX
    schema: z.object({
      title: z.string(),
      pubDate: z.date(),
      tags: z.array(z.string()).default([]),
      draft: z.boolean().default(false),
    }),
  }),
  authors: defineCollection({
    type: 'data', // JSON/YAML
    schema: z.object({
      name: z.string(),
      avatar: z.string().url(),
    }),
  }),
};
```

Querying collections:

```ts
import { getCollection, getEntry } from 'astro:content';

// All published posts
const posts = await getCollection('blog', ({ data }) => !data.draft);

// Single entry
const post = await getEntry('blog', 'my-first-post');
const { Content } = await post.render();
```

## Routing

> Ref: [Routing](https://docs.astro.build/en/guides/routing/), [Dynamic Routes](https://docs.astro.build/en/guides/routing/#dynamic-routes)

| Pattern                       | Result        |
| ----------------------------- | ------------- |
| `src/pages/about.astro`       | `/about`      |
| `src/pages/blog/[slug].astro` | `/blog/:slug` |
| `src/pages/[...path].astro`   | Catch-all     |
| `src/pages/api/data.ts`       | API endpoint  |

Dynamic routes require `getStaticPaths()` in SSG mode:

```ts
export async function getStaticPaths() {
  const posts = await getCollection('blog');
  return posts.map((post) => ({
    params: { slug: post.slug },
    props: { post },
  }));
}
```

## Output Modes

> Ref: [On-demand Rendering](https://docs.astro.build/en/guides/on-demand-rendering/), [Adapters](https://docs.astro.build/en/guides/on-demand-rendering/#official-adapters)

```js
// astro.config.mjs
export default defineConfig({
  output: 'static', // Default: fully pre-rendered at build time
  output: 'server', // SSR: every route rendered on demand
  output: 'hybrid', // Mix: static default, routes can opt into SSR
});
```

For SSR/hybrid, specify an adapter:

```js
import node from '@astrojs/node';
import vercel from '@astrojs/vercel/serverless';
```

## Styling

- Scoped styles by default: `<style>` inside `.astro` files are component-scoped
- Global styles: `<style is:global>` or import in a layout
- CSS variables recommended for theming (no runtime cost)
- Tailwind: use `@astrojs/tailwind` integration

```astro
<style>
  /* Scoped to this component only */
  h1 { color: var(--color-heading); }
</style>
```

## Image Optimization

> Ref: [Images](https://docs.astro.build/en/guides/images/)

Use Astro's built-in `<Image>` component never raw `<img>` for local assets:

```astro
---
import { Image } from 'astro:assets'
import hero from '../assets/hero.jpg'
---
<Image src={hero} alt="Hero" width={800} height={400} />
```

## Common Integrations

| Integration      | Command                  |
| ---------------- | ------------------------ |
| React/Vue/Svelte | `npx astro add react`    |
| Tailwind         | `npx astro add tailwind` |
| MDX              | `npx astro add mdx`      |
| Sitemap          | `npx astro add sitemap`  |

## Anti-Patterns

- Importing Node.js modules in component frontmatter without checking output mode Node APIs are unavailable in static builds; guard with `import.meta.env.SSR`
- Using `client:load` on every interactive component prefer `client:visible` or `client:idle`; `client:load` blocks page hydration
- Storing session/user state in module-level variables in SSR, module scope is shared across requests, causing data leaks between users
- Large framework component islands where a pure Astro component would work each island ships its framework runtime; prefer `.astro` for static content
- Skipping `getStaticPaths()` for dynamic SSG routes build will fail or produce 404s
- Using `<img>` instead of `<Image>` for local assets loses automatic optimization (format conversion, lazy loading, responsive sizes)
- Putting layout logic in `src/pages/` instead of `src/layouts/` duplicates page shells across routes

## Self-Check

- [ ] `client:*` directive used only on components that need browser interactivity
- [ ] Content collections have a schema defined in `src/content/config.ts`
- [ ] Dynamic SSG routes implement `getStaticPaths()`
- [ ] Local images use `<Image>` from `astro:assets`, not raw `<img>`
- [ ] No Node.js-specific imports in SSG-rendered pages without SSR guard
- [ ] Layouts in `src/layouts/`, not duplicated across pages
- [ ] Integrations added via `npx astro add` (not manual config)
- [ ] `output` mode and adapter match the deployment target
