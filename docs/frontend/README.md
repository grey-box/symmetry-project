# Frontend — Desktop Electron Frontend

Cross-platform desktop application built with Electron, React, and TypeScript.

**Source**: `desktop-electron-frontend/`

---

## Tech Stack

- **Electron** v26 — Desktop application framework
- **React** v18 — UI library
- **TypeScript** v5 — Type safety
- **Vite** v4 — Build tool and dev server
- **Electron Forge** v6 — Packaging and distribution
- **Tailwind CSS** v3 — Styling
- **Radix UI / shadcn/ui** — Accessible UI components
- **Axios** v1 — HTTP client (legacy services)
- **React Router** v6 — Client-side routing

---

## Quick Start

```bash
cd desktop-electron-frontend
yarn install
yarn start        # Development mode
yarn build        # Production build
```

---

## Architecture

The application follows Electron's multi-process architecture.

### Main Process (`src/main.ts`)

- Application lifecycle management
- Window creation and management
- Backend process management
- IPC (Inter-Process Communication) handlers
- File system access

### Preload Script (`src/preload.ts`)

- Exposes safe APIs to renderer process via `contextBridge`
- Provides bridge for IPC communication
- Manages config access

### Renderer Process (React)

- Entry: `src/index.tsx` → `src/App.tsx`
- UI rendering and user interaction
- API communication via services
- State management via React Context
- Routing via React Router

---

## Project Structure

```
desktop-electron-frontend/
├── src/
│   ├── main.ts                    # Electron main process
│   ├── preload.ts                 # Preload script
│   ├── index.tsx                  # Renderer entry point
│   ├── App.tsx                    # Root React component
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── ComparisonSection.tsx  # Legacy plain-text comparison
│   │   ├── Layout.tsx
│   │   ├── Navbar.tsx
│   │   ├── PageHeader.tsx
│   │   ├── SectionComparisonView.tsx    # Paragraph-level diff visualization
│   │   ├── StructuredArticleViewer.tsx  # Main article viewer + comparison trigger
│   │   └── TranslationSection.tsx       # Legacy translation workflow
│   ├── constants/
│   │   ├── AppConstants.ts        # Config loader
│   │   └── ROUTES.ts              # Route definitions
│   ├── context/
│   │   └── AppContext.tsx         # Global state management
│   ├── lib/
│   │   └── utils.ts               # Helper functions (cn, etc.)
│   ├── models/
│   │   ├── apis/                  # API request/response types
│   │   ├── enums/                 # Enum definitions
│   │   └── structured-wiki.ts     # TypeScript interfaces matching backend Pydantic models
│   ├── pages/
│   │   ├── Home.tsx               # Tab-based layout (primary tab first)
│   │   └── Settings.tsx
│   └── services/
│       ├── axios.ts               # Axios instance with IPC config
│       ├── compareArticles.ts     # Legacy comparison API calls
│       ├── fetchArticle.ts        # Article fetching API
│       ├── structuredWikiService.ts  # Primary API service (uses raw fetch())
│       └── translateArticle.ts    # Translation API calls
├── components.json                # shadcn/ui configuration
├── forge.config.js                # Electron Forge configuration
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.main.config.mjs
├── vite.preload.config.mjs
└── vite.renderer.config.mjs
```

---

## Key Design Decisions

- **Tab order**: Structured Article (primary) → Translation (Legacy) → AI Comparison (Legacy)
- **API base URL**: `structuredWikiService.ts` hardcodes `API_BASE_URL = 'http://127.0.0.1:8000'`. Legacy services use Axios via `getAxiosInstance()` with IPC config.
- **`structuredWikiService`** uses raw `fetch()` while legacy services use Axios — do not mix the two patterns.
- **TypeScript models** in `src/models/structured-wiki.ts` mirror backend Pydantic models using `snake_case` field names.

---

## Configuration

The frontend reads backend URL and other settings from `config.json` (loaded in `AppConstants.ts` via Electron IPC). The default values are in `config.default.json` at the project root.

---

## Conventions

- 2-space indentation
- `PascalCase` for components and types
- `camelCase` for functions, variables, services
- Interfaces match backend Pydantic models (`snake_case` field names)
