# WebSocket Real-Time Updates

This document describes the WebSocket implementation for real-time transaction analysis updates.

## Overview

The frontend now supports real-time updates via WebSocket connection to the backend. This allows users to see agent execution progress live as transactions are analyzed.

## Architecture

### Custom Hooks

#### `useWebSocket(options)`

Custom hook for managing WebSocket connections with automatic reconnection.

**Location:** `src/hooks/useWebSocket.ts`

**Parameters:**
```typescript
{
  transactionId?: string;      // Optional transaction ID filter
  autoConnect?: boolean;        // Auto-connect on mount (default: true)
  maxReconnectDelay?: number;   // Max reconnect delay in ms (default: 30000)
}
```

**Returns:**
```typescript
{
  events: WebSocketEvent[];     // Array of received events
  isConnected: boolean;         // Connection status
  lastEvent: WebSocketEvent | null;  // Most recent event
  connect: () => void;          // Manual connect function
  disconnect: () => void;       // Manual disconnect function
}
```

**Features:**
- ✅ Automatic reconnection with exponential backoff (1s → 2s → 4s → ... → 30s max)
- ✅ Connection state management
- ✅ Event history
- ✅ Cleanup on unmount
- ✅ Optional transaction filtering

**Example:**
```typescript
"use client";

import { useWebSocket } from "@/hooks/useWebSocket";

function MyComponent({ transactionId }: { transactionId: string }) {
  const { events, isConnected } = useWebSocket({
    transactionId,
    autoConnect: true,
  });

  return (
    <div>
      <p>Status: {isConnected ? "Connected" : "Disconnected"}</p>
      <p>Events: {events.length}</p>
    </div>
  );
}
```

---

#### `useTransactions(options)`

Custom hook for polling transactions with auto-refresh.

**Location:** `src/hooks/useTransactions.ts`

**Parameters:**
```typescript
{
  limit?: number;           // Number of transactions to fetch (default: 100)
  offset?: number;          // Offset for pagination (default: 0)
  refreshInterval?: number; // Auto-refresh interval in seconds (default: 30, 0 = disabled)
}
```

**Returns:**
```typescript
{
  transactions: TransactionRecord[];  // Current transactions
  isLoading: boolean;                 // Loading state
  error: string | null;               // Error message if any
  refresh: () => Promise<void>;       // Manual refresh function
}
```

**Features:**
- ✅ Initial fetch on mount
- ✅ Automatic polling at specified interval
- ✅ Manual refresh capability
- ✅ Error handling
- ✅ Cleanup on unmount

**Example:**
```typescript
"use client";

import { useTransactions } from "@/hooks/useTransactions";

function TransactionsList() {
  const { transactions, isLoading, refresh } = useTransactions({
    limit: 50,
    refreshInterval: 30, // Refresh every 30 seconds
  });

  return (
    <div>
      <button onClick={refresh}>Refresh</button>
      {/* Render transactions */}
    </div>
  );
}
```

---

### Components

#### `AgentTraceTimeline` (Enhanced)

Now accepts `liveEvents` prop for real-time agent status updates.

**Location:** `src/components/agents/AgentTraceTimeline.tsx`

**New Props:**
```typescript
{
  trace: AgentTraceEntry[];       // Static trace data
  liveEvents?: WebSocketEvent[];  // Real-time events (optional)
}
```

**Live Features:**
- 🔵 **Running agents**: Blue pulsing dot with spinner icon
- ✅ **Just completed**: Fade-in animation (2 second window)
- 📡 **Live badge**: Shows when receiving WebSocket events
- ⚡ **Automatic state mapping**: Maps WS events to agent states

**Event Mapping:**
- `agent_started` → Agent shows "running" state with pulse animation
- `agent_completed` → Agent transitions to completed with fade-in animation
- `decision_ready` → Full trace is complete

**Example:**
```typescript
import { useWebSocket } from "@/hooks/useWebSocket";
import { AgentTraceTimeline } from "@/components/agents/AgentTraceTimeline";

function TransactionDetail({ transactionId, trace }) {
  const { events } = useWebSocket({ transactionId });

  return (
    <AgentTraceTimeline
      trace={trace}
      liveEvents={events}  // Pass live events for animations
    />
  );
}
```

---

#### `WebSocketStatus`

Reusable connection status indicator.

**Location:** `src/components/common/WebSocketStatus.tsx`

**Props:**
```typescript
{
  isConnected: boolean;
  showLabel?: boolean;  // Show "Connected/Disconnected" text (default: true)
}
```

**Variants:**
- 🟢 **Connected**: Green badge with wifi icon + pulse animation
- 🔴 **Disconnected**: Red badge with wifi-off icon

**Example:**
```typescript
import { WebSocketStatus } from "@/components/common/WebSocketStatus";

function Header({ isConnected }: { isConnected: boolean }) {
  return <WebSocketStatus isConnected={isConnected} />;
}
```

---

#### `TransactionDetailClient`

Client component wrapper for transaction detail page with WebSocket.

**Location:** `src/components/transactions/TransactionDetailClient.tsx`

**Features:**
- ✅ Automatic WebSocket connection for transaction
- ✅ Connection status indicator in header
- ✅ Live events passed to AgentTraceTimeline
- ✅ Graceful degradation if WebSocket unavailable

---

#### `TransactionsClient`

Client component for transactions list with auto-refresh.

**Location:** `src/components/transactions/TransactionsClient.tsx`

**Features:**
- ✅ Auto-refresh every 30 seconds (configurable)
- ✅ Manual refresh button
- ✅ Auto-refresh badge indicator
- ✅ Loading state during refresh
- ✅ Server-side initial data + client-side polling

---

## WebSocket Protocol

### Connection URL

```
ws://localhost:8000/api/v1/ws/transactions
```

Optional query parameter:
```
?transaction_id=T-1001  // Filter events for specific transaction
```

### Event Types

#### 1. Agent Started
```json
{
  "event": "agent_started",
  "agent": "TransactionContext",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {}
}
```

#### 2. Agent Completed
```json
{
  "event": "agent_completed",
  "agent": "TransactionContext",
  "timestamp": "2025-01-15T10:30:01Z",
  "data": {
    "duration_ms": 150,
    "status": "success"
  }
}
```

#### 3. Decision Ready
```json
{
  "event": "decision_ready",
  "timestamp": "2025-01-15T10:30:05Z",
  "data": {
    "transaction_id": "T-1001",
    "decision": "CHALLENGE"
  }
}
```

---

## Environment Variables

### Frontend

Create `.env.local` in `frontend/`:

```bash
# WebSocket URL (optional, defaults to ws://localhost:8000)
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# API URL (optional, defaults to http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Usage Examples

### Example 1: Transaction Detail with Live Updates

```typescript
// pages/transactions/[id]/page.tsx (server component)
import { TransactionDetailClient } from "@/components/transactions/TransactionDetailClient";

export default async function Page({ params }) {
  const { id } = await params;
  const [detail, trace] = await Promise.all([
    getTransactionDetail(id),
    getTransactionTrace(id),
  ]);

  return (
    <TransactionDetailClient
      transactionId={id}
      detail={detail}
      trace={trace}
    />
  );
}
```

The client component automatically:
1. Connects to WebSocket for this transaction
2. Shows connection status
3. Passes live events to AgentTraceTimeline
4. Animates agents as they run and complete

---

### Example 2: Transaction List with Auto-Refresh

```typescript
// pages/transactions/page.tsx (server component)
import { TransactionsClient } from "@/components/transactions/TransactionsClient";

export default async function Page() {
  const initialTransactions = await getTransactions(100, 0);

  return (
    <TransactionsClient
      initialTransactions={initialTransactions}
      refreshInterval={30}  // Refresh every 30 seconds
    />
  );
}
```

The client component:
1. Shows initial server-fetched data immediately
2. Polls for updates every 30 seconds
3. Provides manual refresh button
4. Shows auto-refresh badge

---

### Example 3: Custom Component with WebSocket

```typescript
"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import { WebSocketStatus } from "@/components/common/WebSocketStatus";

export function LiveMonitor() {
  const { events, isConnected, lastEvent } = useWebSocket({
    autoConnect: true,
  });

  return (
    <div>
      <WebSocketStatus isConnected={isConnected} />

      {lastEvent && (
        <div>
          Last event: {lastEvent.event} at {lastEvent.timestamp}
        </div>
      )}

      <div>
        <h3>Event History ({events.length})</h3>
        {events.map((event, i) => (
          <div key={i}>
            {event.event} - {event.agent || 'global'}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Reconnection Strategy

The WebSocket hook implements exponential backoff for reconnections:

1. **Initial connection fails** → Retry after 1 second
2. **Second failure** → Retry after 2 seconds
3. **Third failure** → Retry after 4 seconds
4. **Fourth failure** → Retry after 8 seconds
5. **Continues doubling** → Up to maximum of 30 seconds

Connection is only attempted if `shouldConnect` is true (controlled by `disconnect()` call).

---

## Performance Considerations

### WebSocket

- **Single connection per page**: Each transaction detail page opens one WebSocket
- **Automatic cleanup**: Connections closed on page unmount
- **Filtered events**: Transaction-specific connections only receive relevant events
- **Minimal bandwidth**: Only state changes are sent, not full agent outputs

### Polling

- **Configurable interval**: Default 30s, can be disabled (set to 0)
- **Smart caching**: Uses SWR-like pattern with initial server data
- **Manual refresh**: Users can force refresh without waiting for interval
- **Conditional rendering**: Only shows auto-refresh badge when enabled

---

## Troubleshooting

### WebSocket not connecting

1. **Check backend is running**:
   ```bash
   cd backend
   python -m uv run uvicorn app.main:app --reload
   ```

2. **Verify WebSocket endpoint**:
   ```bash
   # Test with wscat (npm install -g wscat)
   wscat -c ws://localhost:8000/api/v1/ws/transactions
   ```

3. **Check browser console**: Look for connection errors
4. **Verify environment variables**: Ensure `NEXT_PUBLIC_WS_URL` is correct

### No live updates showing

1. **Check isConnected state**: Should be `true`
2. **Verify events array**: Should receive events when analysis runs
3. **Check transaction ID**: Ensure it matches the analyzing transaction
4. **Run analysis**: WebSocket events only sent during active analysis

### Polling not working

1. **Check refreshInterval**: Should be > 0
2. **Verify API endpoint**: Backend should be responding to `/api/v1/transactions`
3. **Check browser console**: Look for fetch errors
4. **Test manual refresh**: Click refresh button to isolate issue

---

## Testing

### Manual Testing

1. **Start backend**:
   ```bash
   cd backend
   python -m uv run uvicorn app.main:app --reload
   ```

2. **Start frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Trigger analysis**:
   ```bash
   cd backend
   python seed_test.py
   ```

4. **Watch in browser**:
   - Go to http://localhost:3000/transactions
   - Click on a transaction
   - Watch for:
     - 🟢 Green "Connected" badge in header
     - 📡 Blue "Live" badge on timeline
     - 🔵 Pulsing blue dots on running agents
     - ✅ Fade-in animation when agents complete

---

## Future Enhancements

Potential improvements for future iterations:

- [ ] **Dashboard live feed**: Show recent events on dashboard
- [ ] **Notification sounds**: Audio alerts for important events
- [ ] **Event filtering**: Client-side filtering by event type
- [ ] **Performance metrics**: Track connection stability
- [ ] **Batch operations**: WebSocket support for batch analysis
- [ ] **SWR integration**: Replace polling with SWR for better caching
- [ ] **Progressive updates**: Stream partial results as they become available

---

## Summary

The WebSocket implementation provides:

✅ **Real-time updates** for transaction analysis
✅ **Automatic reconnection** with exponential backoff
✅ **Live agent status** with animations
✅ **Connection indicators** for user awareness
✅ **Polling fallback** for transactions list
✅ **TypeScript strict mode** compliance
✅ **Graceful degradation** when WebSocket unavailable
✅ **Production-ready** error handling and cleanup

All components follow the established patterns from the codebase and integrate seamlessly with the existing architecture.
