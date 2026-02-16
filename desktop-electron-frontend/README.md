# Project Symmetry - Desktop Electron Frontend

A cross-platform desktop application built with Electron, React, and TypeScript for cross-language Wikipedia article gap analysis.

## Overview

This frontend application provides a user-friendly interface for translating, comparing, and analyzing Wikipedia articles across different languages. It communicates with a FastAPI backend for semantic analysis and article processing.

## Tech Stack

- **Electron** v26 - Desktop application framework
- **React** v18 - UI library
- **TypeScript** v5 - Type safety
- **Vite** v4 - Build tool and dev server
- **Electron Forge** v6 - Packaging and distribution
- **Tailwind CSS** v3 - Styling
- **Radix UI** - Accessible UI components (shadcn/ui)
- **Axios** v1 - HTTP client
- **React Router** v6 - Client-side routing

## Architecture

The application follows Electron's multi-process architecture:

### Main Process (Node.js)
- **Location**: `src/main.ts`
- **Responsibilities**:
  - Application lifecycle management
  - Window creation and management
  - Backend process management
  - IPC (Inter-Process Communication) handlers
  - File system access

### Preload Script
- **Location**: `src/preload.ts`
- **Responsibilities**:
  - Exposes safe APIs to renderer process via `contextBridge`
  - Provides bridge for IPC communication
  - Manages config access

### Renderer Process (React)
- **Entry**: `src/index.tsx` → `src/App.tsx`
- **Responsibilities**:
  - UI rendering and user interaction
  - API communication via services
  - State management via React Context
  - Routing via React Router

## Project Structure

```
desktop-electron-frontend/
├── src/
│   ├── main.ts                 # Electron main process
│   ├── preload.ts              # Preload script
│   ├── index.tsx               # Renderer entry point
│   ├── App.tsx                 # Root React component
│   ├── assets/                 # Static assets (images, CSS)
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── form.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── select.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── table.tsx
│   │   │   └── textarea.tsx
│   │   ├── ComparisonSection.tsx
│   │   ├── Layout.tsx
│   │   ├── Navbar.tsx
│   │   ├── PageHeader.tsx
│   │   ├── StructuredArticleViewer.tsx
│   │   └── TranslationSection.tsx
│   ├── constants/              # Application constants
│   │   ├── AppConstants.ts     # Config loader
│   │   └── ROUTES.ts           # Route definitions
│   ├── context/                # React Context
│   │   └── AppContext.tsx      # Global state management
│   ├── lib/                    # Utility functions
│   │   └── utils.ts            # Helper functions (cn, etc.)
│   ├── models/                 # TypeScript types
│   │   ├── apis/               # API request/response types
│   │   │   ├── FetchArticleRequest.ts
│   │   │   ├── FetchArticleResponse.ts
│   │   │   ├── TranslateArticleRequest.ts
│   │   │   └── TranslateArticleResponse.ts
│   │   ├── enums/              # Enum definitions
│   │   │   ├── FetchArticleResponse.ts
│   │   │   └── TranslationTool.ts
│   │   ├── FetchArticleRequest.ts
│   │   ├── Phase.ts
│   │   ├── SelectData.ts
│   │   ├── TranslationFormType.ts
│   │   ├── TranslationSettingsFormType.ts
│   │   └── structured-wiki.ts
│   ├── pages/                  # Page components
│   │   ├── Home.tsx
│   │   └── Settings.tsx
│   └── services/               # API services
│       ├── axios.ts            # Axios instance configuration
│       ├── compareArticles.ts  # Comparison API calls
│       ├── fetchArticle.ts     # Article fetching API
│       ├── structuredWikiService.ts
│       └── translateArticle.ts # Translation API calls
├── components.json             # shadcn/ui configuration
├── forge.config.js             # Electron Forge configuration
├── index.html                  # HTML template
├── package.json                # Dependencies and scripts
├── tailwind.config.js          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
├── vite.main.config.mjs        # Vite config for main process
├── vite.preload.config.mjs     # Vite config for preload
└── vite.renderer.config.mjs   # Vite config for renderer
```

## Getting Started

### Prerequisites
- Node.js v18+
- Yarn or npm
- Backend API server (FastAPI)

### Installation

```bash
# Install dependencies
yarn install

# or with npm
npm install
```

### Development

```bash
# Start development server with hot reload
yarn start

# The app will:
# 1. Start the Electron main process
# 2. Launch the React dev server
# 3. Start the backend API (if configured)
# 4. Open the application window
```

### Configuration

The application reads configuration from a `config.json` file in the parent directory:

```json
{
  "port": 8000,
  "backendBaseUrl": "http://127.0.0.1:8000"
}
```

Configuration is loaded via:
1. Main process reads `config.json`
2. Config is exposed to renderer via IPC
3. Services use config to set API base URL

## Available Scripts

```bash
yarn start              # Start development server
yarn package            # Package application for distribution
yarn make               # Create distributable packages
yarn publish            # Publish releases
yarn lint               # Run linter (not configured yet)
```

## Key Features

### IPC Communication

The app uses Electron's IPC (Inter-Process Communication) for secure data exchange:

**From Renderer to Main:**
```typescript
// In renderer process
const config = await window.electronAPI.getAppConfig();
```

**IPC Handlers (main.ts):**
- `get-app-config` - Retrieve application configuration
- `start-backend` - Start backend API process

### API Services

All API calls go through services in `src/services/`:

```typescript
import { axiosInstance } from '@/services/axios';
import { fetchArticle } from '@/services/fetchArticle';
import { translateArticle } from '@/services/translateArticle';
import { compareArticles } from '@/services/compareArticles';
```

The axios instance is configured with:
- Dynamic base URL from config
- 10-second timeout
- Request/response interceptors for debugging

### Routing

Uses React Router v6 with HashRouter (required for Electron):

```typescript
<HashRouter>
  <Routes>
    <Route path={ROUTES.BASE} element={<Layout />}>
      <Route index element={<Home />} />
      <Route path={ROUTES.SETTINGS} element={<Settings />} />
    </Route>
  </Routes>
</HashRouter>
```

### State Management

Uses React Context for global state:

```typescript
const { 
  translationPhase, 
  selectedArticle,
  comparisonResult,
  updateTranslationPhase 
} = useContext(AppContext);
```

### UI Components

Built with shadcn/ui + Tailwind CSS:

```typescript
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
```

## Backend Integration

### Automatic Backend Startup

The main process automatically starts the Python backend:

```typescript
// In main.ts - createWindow()
execFile('python3', ['app/main.py'], {
  cwd: path.join(process.cwd(), '../backend-fastapi'),
  timeout: 10000
}, (error, stdout, stderr) => {
  console.log('[INFO] Backend API started');
});
```

### API Endpoints

The frontend communicates with these backend endpoints:

- `POST /symmetry/v1/articles/compare` - Compare two articles (semantic comparison)
- `GET /symmetry/v1/wiki/articles?query={url|title}&lang={code}` - Fetch Wikipedia article
- `GET /symmetry/v1/wiki/structured-article?query={url|title}&lang={code}` - Get structured article
- `POST /symmetry/v1/comparison/translate_text` - Translate text
- `GET /symmetry/v1/comparison/translate_text` - Translate text (GET)
- `GET /models/translation` - List available translation models
- `GET /models/translation/selected` - Get selected translation model
- `GET /models/comparison` - List available comparison models
- `GET /models/comparison/selected` - Get selected comparison model

## Building for Distribution

### Package

```bash
yarn package
```

Creates an unpacked application in `out/` directory.

### Make Distributables

```bash
yarn make
```

Creates platform-specific installers in `out/make/`:

- **Windows**: `.exe` (via Squirrel)
- **macOS**: `.dmg` or `.zip`
- **Linux**: `.deb` and `.rpm`

### Publish to GitHub

```bash
yarn publish
```

Requires GitHub token and proper repository configuration in `forge.config.js`.

## Development Workflow

### 1. Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `src/constants/ROUTES.ts`
3. Add route in `src/App.tsx`

```typescript
// src/constants/ROUTES.ts
export const ROUTES = {
  BASE: '/',
  NEW_PAGE: '/new-page',
};

// src/App.tsx
<Route path={ROUTES.NEW_PAGE} element={<NewPage />} />
```

### 2. Adding a New API Service

1. Create service file in `src/services/`
2. Define request/response types in `src/models/apis/`
3. Use `axiosInstance` for API calls

```typescript
// src/services/myService.ts
import { axiosInstance } from './axios';
import { MyRequest, MyResponse } from '@/models/apis/MyRequest';

export const myApiCall = async (request: MyRequest): Promise<MyResponse> => {
  const response = await axiosInstance.post('/api/endpoint', request);
  return response.data;
};
```

### 3. Adding UI Components

Using shadcn/ui CLI (if available) or manually:

```typescript
// Manual component creation
import * as React from "react"
import { cn } from "@/lib/utils"

interface MyComponentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const MyComponent = React.forwardRef<HTMLDivElement, MyComponentProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("base-class", className)} {...props} />
  )
)
```

## Type System

TypeScript configuration includes:
- Strict mode enabled
- Path aliases: `@/*` → `./src/*`
- No unchecked indexed access
- ES6 target

### Common Type Locations
- **API Types**: `src/models/apis/`
- **Component Props**: Inline or separate files
- **Forms**: `src/models/*FormType.ts`
- **Enums**: `src/models/enums/`

## Styling

### Tailwind CSS

All components use Tailwind utility classes:

```tsx
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
  <h2 className="text-2xl font-bold text-gray-900">Title</h2>
</div>
```

### Custom Styles

Global styles in `src/index.css`:
- Tailwind directives
- Custom CSS variables
- Component-specific styles

## Troubleshooting

### Backend Not Starting

**Issue**: Backend fails to start when app launches

**Solutions**:
1. Check if Python 3 is installed: `python3 --version`
2. Verify backend path in `src/main.ts`
3. Check console logs in DevTools (Cmd+Opt+I)
4. Manually start backend: `cd ../symmetry-unified-backend && ./start.sh`

### IPC Communication Errors

**Issue**: Cannot access `window.electronAPI`

**Solutions**:
1. Ensure preload script is loaded in main.ts
2. Check `webPreferences.preload` path
3. Verify contextBridge is configured in preload.ts

### Build Errors

**Issue**: Vite build fails

**Solutions**:
1. Clear node_modules: `rm -rf node_modules && yarn install`
2. Check TypeScript errors: `yarn tsc --noEmit`
3. Verify all imports use `@/` alias or relative paths

### Hot Reload Not Working

**Issue**: Changes don't reflect in app

**Solutions**:
1. Ensure development mode is running
2. Check if Vite dev server is running
3. Restart the app: Quit and run `yarn start`

### Port Already in Use

**Issue**: Port 8000 already in use

**Solutions**:
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change backend port in config.json
```

## Environment Variables

The app doesn't use `.env` files directly. Configuration is managed via:
- `config.json` - Runtime configuration
- `forge.config.js` - Build configuration
- `tsconfig.json` - TypeScript configuration

## Testing

Currently no automated tests are configured. To add testing:

```bash
# Install testing dependencies
yarn add -D @testing-library/react @testing-library/jest-dom vitest

# Run tests (once configured)
yarn test
```

## Performance Optimization

### Current Optimizations
- Vite's fast HMR (Hot Module Replacement)
- Code splitting via dynamic imports
- Lazy loading of routes (potential enhancement)
- Axios request/response caching (potential enhancement)

### Recommended Enhancements
- Implement React.memo for expensive components
- Add virtual scrolling for large lists
- Implement service workers for offline caching
- Use React Suspense for code-split boundaries

## Security Considerations

### Current Security Measures
- contextBridge for safe IPC communication
- No direct Node.js access in renderer
- Content Security Policy (CSP) headers (potential)
- Input validation via TypeScript and Pydantic

### Best Practices
- Never expose sensitive data via IPC
- Validate all user input
- Use HTTPS for API calls in production
- Keep dependencies updated

## Contributing

When contributing to the frontend:

1. Follow existing code style and patterns
2. Use TypeScript for all new code
3. Add proper type definitions for new APIs
4. Use existing UI components when possible
5. Test on all target platforms (Windows, macOS, Linux)
6. Update documentation for new features

## Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
- [Vite Documentation](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Electron Forge](https://www.electronforge.io)
