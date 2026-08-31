# AyoChat Mobile Companion PWA Architecture

## Overview
The AyoChat Mobile Companion PWA is a progressive web application that serves as a mobile-first dashboard for Human-in-the-Loop (HITL) YouTube comment moderation. It replaces the Telegram webhook interface with a direct mobile application built with Next.js, TypeScript, and Material 3 Expressive design system.

## Technology Stack

### Frontend
- **Framework**: Next.js 16.3.3 with App Router and TypeScript
- **Styling**: Tailwind CSS with custom Material 3 Expressive design tokens
- **Icons**: Lucide React
- **PWA**: next-pwa for service worker and manifest generation
- **State Management**: React hooks (useState, useEffect, useCallback)
- **Utilities**: clsx and tailwind-merge for conditional styling

### Backend Integration
- **API**: FastAPI with new PWA-specific endpoints
- **Database**: SQLite with existing HITL state management
- **Communication**: REST API with JSON payloads

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mobile PWA (Next.js)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Hero Page  │───▶│  Queue Page  │───▶│  Edit Modal  │     │
│  │  (Landing)   │    │  (HITL Feed) │    │  (Bottom Sheet)│     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                     │                     │              │
│         │                     │                     │              │
│  ┌──────▼────────────────────▼────────────────────▼──────┐  │
│  │              API Client (lib/api.ts)                  │  │
│  │  - getQueue()    - resolveComment()                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
└──────────────────────────│───────────────────────────────────┘
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (src/api/)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         PWA Endpoints (New)                              │  │
│  │  GET  /api/queue     - Fetch pending comments           │  │
│  │  POST /api/resolve    - Unified approve/skip/edit endpoint │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      Existing HITL Endpoints (Backward Compatible)       │  │
│  │  GET  /api/hitl/pending  - Original queue endpoint       │  │
│  │  POST /api/hitl/approve/{id} - Original approve         │  │
│  │  POST /api/hitl/edit/{id}    - Original edit            │  │
│  │  POST /api/hitl/skip/{id}    - Original skip             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            HITLDatabase (SQLite)                        │  │
│  │  - State management                                   │  │
│  │  - CRUD operations                                    │  │
│  │  - Fine-tuning dataset export                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            ActionDispatcher                              │  │
│  │  - YouTube reply dispatch                              │  │
│  │  - Synthetic memory logging                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

### Frontend Structure
```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with PWA metadata
│   ├── page.tsx                # Hero landing page
│   ├── queue/
│   │   └── page.tsx            # HITL queue interface
│   └── globals.css             # Global styles & M3 tokens
├── components/
│   ├── hero/
│   │   └── GlassHero.tsx       # Liquid glass hero component
│   ├── queue/
│   │   ├── QueueFeed.tsx       # Main queue container
│   │   └── CommentCard.tsx     # Individual comment card
│   ├── ui/
│   │   ├── GlassCard.tsx       # Glassmorphic card
│   │   ├── M3FAB.tsx           # Material 3 FAB
│   │   ├── M3Button.tsx        # Material 3 button
│   │   └── GlassBottomSheet.tsx # Edit dialog
│   └── layout/
│       ├── MobileNav.tsx      # Mobile navigation
│       └── AppHeader.tsx       # Glassmorphic header
├── lib/
│   ├── api.ts                  # API client functions
│   └── utils.ts                # Utility functions (cn)
└── public/
    ├── manifest.json           # PWA manifest
    └── icons/                  # App icons
```

## Data Flow

### Queue Loading Flow
1. User opens PWA → Hero page displays
2. User clicks "Enter Dashboard" → Navigate to `/queue`
3. `QueueFeed` component mounts → `useEffect` triggers `api.getQueue()`
4. API client calls `GET /api/queue` → FastAPI backend
5. Backend queries SQLite for `PENDING_APPROVAL` comments
6. Returns list of `HITLCommentRecord` objects
7. Frontend renders `CommentCard` components for each item
8. Polling every 30 seconds for updates

### Action Resolution Flow
1. User clicks Approve/Skip/Edit on a comment card
2. `QueueFeed` component calls appropriate handler function
3. Handler calls `api.resolveComment()` with action payload
4. API client calls `POST /api/resolve` → FastAPI backend
5. Backend processes action:
   - **Approve**: Updates status to `APPROVED`, dispatches to YouTube, exports to fine-tuning dataset
   - **Skip**: Updates status to `SKIPPED`, no dispatch
   - **Edit**: Updates status to `EDITED`, calculates vector delta, dispatches edited reply
6. Backend returns success response
7. Frontend removes card from queue (optimistic update)
8. Success feedback displayed to user

## API Integration

### New PWA Endpoints

#### GET /api/queue
Fetches pending comments for the mobile queue interface.

**Request Parameters:**
- `limit` (optional, default: 20): Maximum number of items to return
- `video_id` (optional): Filter by specific video ID

**Response:** Array of `HITLCommentRecord` objects

**Example:**
```json
GET /api/queue?limit=20
[
  {
    "id": "uuid-1",
    "comment_id": "UgzKb6Z9Z9Z9Z9Z9Z9Z9Z9A",
    "video_id": "dQw4w9WgXcQ",
    "video_title": "Never Gonna Give You Up",
    "author_name": "RickRoller42",
    "input_comment": "This comment is amazing!",
    "model_draft_reply": "Thanks for the kind words!",
    "applied_vectors": {
      "code_switch_alpha": 0.85,
      "sovereignty_beta": "ELEVATE",
      "frequency_gamma": 3,
      "token_economy_tau": "Pass (1 Sentence)"
    },
    "status": "PENDING_APPROVAL",
    ...
  }
]
```

#### POST /api/resolve
Unified endpoint for HITL resolution from mobile PWA.

**Request Body:**
```json
{
  "record_id": "uuid-1",
  "action": "approve",  // or "skip" or "edit"
  "edited_reply": "Optional edited text",
  "target_alpha": 0.90,  // Optional for edit action
  "notes": "Resolved via Mobile PWA"
}
```

**Response:** `TelegramActionResponse` object

**Example:**
```json
{
  "status": "success",
  "action": "approved",
  "record_id": "uuid-1",
  "comment_id": "UgzKb6Z9Z9Z9Z9Z9Z9Z9Z9A",
  "reply_text": "Thanks for the kind words!",
  "alignment_delta": 0.0,
  "dispatched": true,
  "message": "Comment approved via Mobile PWA"
}
```

## Design System

### Material 3 Expressive Implementation

The PWA uses Material 3 Expressive design principles with a custom Gemini AI liquid glass aesthetic:

#### Design Tokens
```css
/* Liquid Glass Theme */
--glass-bg: rgba(15, 23, 42, 0.6);
--glass-border: rgba(255, 255, 255, 0.1);
--luminescent-glow: rgba(99, 102, 241, 0.3);
--shiny-edge: rgba(255, 255, 255, 0.2);

/* Material 3 Colors */
--m3-primary: #6366f1;
--m3-secondary: #62571e;
--m3-tertiary: #7c5800;
--m3-error: #ba1a1a;

/* M3 Expressive Radius */
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 24px;
--radius-full: 9999px;

/* M3 Motion */
--motion-emphasized: cubic-bezier(0.2, 0.0, 0.0, 1.0);
--duration-short: 150ms;
--duration-medium: 250ms;
```

#### Component Specifications

**GlassCard**
- Background: Glassmorphic with backdrop blur
- Border: Shiny edge highlight on top
- Shadow: Material 3 elevation 2
- Radius: 12px (M3 Expressive)

**M3FAB (Floating Action Button)**
- Size: 56px (medium) or 80px (large)
- Radius: 24px (M3 Expressive)
- Shadow: Material 3 elevation 3
- Motion: Hover lift (-2px Y), active scale (0.95)

**M3Button**
- Radius: Full (9999px)
- Variants: Filled, Outlined, Text
- Motion: Background color transition (150ms)

**GlassBottomSheet**
- Background: Glassmorphic with backdrop blur
- Animation: Slide up from bottom (300ms ease-out)
- Handle: Draggable indicator at top
- Max height: 70vh of screen

## State Management

The PWA uses React hooks for state management without external libraries:

### Queue State
```typescript
const [queue, setQueue] = useState<HITLQueueItem[]>([]);
const [loading, setLoading] = useState(true);
const [refreshing, setRefreshing] = useState(false);
```

### Edit State
```typescript
const [editingItem, setEditingItem] = useState<HITLQueueItem | null>(null);
const [editedText, setEditedText] = useState("");
const [processing, setProcessing] = useState(false);
```

### Polling
```typescript
useEffect(() => {
  fetchQueue();
  const interval = setInterval(fetchQueue, 30000); // 30-second polling
  return () => clearInterval(interval);
}, []);
```

## PWA Configuration

### Manifest Settings
- **Name**: AyoChat Mobile Companion
- **Short Name**: AyoChat
- **Display Mode**: Standalone
- **Orientation**: Portrait
- **Theme Color**: #6366f1 (Indigo)
- **Background Color**: #030407 (Dark)
- **Icons**: 192x192 and 512x512 PNG

### Service Worker
- **Cache Strategy**: Cache-first for static assets
- **Offline Support**: Basic offline page
- **Update Strategy**: Skip waiting for new versions
- **Scope**: Root directory

## Performance Optimizations

### Frontend
- **Static Generation**: Queue page pre-rendered as static content
- **Code Splitting**: Automatic route-based splitting
- **Image Optimization**: Next.js Image component for icons
- **CSS Optimization**: Tailwind purges unused styles in production

### Backend
- **SQLite WAL Mode**: Improved concurrent access
- **Connection Pooling**: Reusable database connections
- **Efficient Queries**: Indexed queries on status and video_id

## Mobile Optimizations

### Responsive Design
- **Mobile-First**: Designed for 375px+ viewport width
- **Touch Targets**: Minimum 44px for interactive elements
- **Viewport Meta**: Proper mobile viewport configuration
- **Safe Area**: viewport-fit=cover for notched devices

### Performance
- **Bundle Size**: Optimized production build
- **Loading States**: Skeleton screens and loading indicators
- **Optimistic Updates**: Immediate UI feedback before API response
- **Error Handling**: Graceful degradation on network errors

## Security Considerations

### API Security
- **CORS**: Configured for specific origins in production
- **Input Validation**: Pydantic models validate all requests
- **SQL Injection**: Parameterized queries via SQLite
- **Rate Limiting**: FastAPI middleware can be added

### PWA Security
- **HTTPS Required**: PWA requires HTTPS in production
- **Content Security Policy**: Can be added for additional security
- **Secure Context**: Service workers only run in secure contexts

## Deployment

### Development
```bash
cd frontend
npm run dev
```
- Runs on http://localhost:3000
- HMR enabled for fast development
- PWA disabled in development mode

### Production
```bash
cd frontend
npm run build
npm start
```
- Optimized production build
- PWA enabled with service worker
- Static files served efficiently

### Environment Variables
- `NEXT_PUBLIC_API_URL`: Backend API URL (defaults to window.location.origin)
- `NODE_ENV`: Production/development mode

## Troubleshooting

### Build Issues
- **Turbopack Warnings**: Add `turbopack: {}` to next.config.ts
- **TypeScript Errors**: Ensure all interfaces are properly exported
- **Import Errors**: Check relative import paths

### API Connection Issues
- **CORS Errors**: Verify FastAPI CORS configuration
- **Network Errors**: Check API_BASE_URL configuration
- **Timeout Errors**: Increase fetch timeout in api.ts

### PWA Installation Issues
- **iOS Safari**: Requires HTTPS and proper manifest
- **Android Chrome**: Check manifest validation
- **Service Worker**: Verify scope and registration

## Future Enhancements (Phase 2)

### Vector Visualization
- 4D semiotic vector display with M3 Progress Indicators
- Real-time vector delta visualization
- Color-coded vector ranges

### Advanced Features
- Vector adjustment slider in edit flow
- Real-time WebSocket updates
- Push notifications for queue updates
- Advanced PWA features (background sync, push)

## Conclusion

The AyoChat Mobile Companion PWA provides a production-ready mobile interface for HITL moderation with:
- Material 3 Expressive design system
- Gemini AI liquid glass aesthetic
- Mobile-first responsive design
- PWA capabilities for offline usage
- Seamless integration with existing FastAPI backend
- Backward compatibility with Telegram webhook system

The architecture prioritizes performance, user experience, and maintainability while providing a solid foundation for future enhancements.