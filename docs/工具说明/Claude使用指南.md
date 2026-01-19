---
category: 工具说明
title: Claude使用指南
tags: ['Claude', 'AI', '工具']
description: 如何在SmokeSignal项目中有效使用Claude AI助手
priority: low
last_updated: 2026-01-19
---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmokeSignal Analytics is a single-page React application for e-commerce customer service analytics. It provides a Notion-style dashboard for analyzing customer chat history, sentiment patterns, purchase behavior, and AI-powered customer insights. The application targets e-commerce customer service teams and sales analysts working with platforms like Taobao/Tmall (千牛工作台 - Qianniu Workbench).

**Origin:** Built with Google AI Studio (https://ai.studio/apps/drive/14aS21FRXtWxJc9UKqX5inwFDswfXQW6t)

## Development Commands

```bash
# Install dependencies
npm install

# Development server (runs on http://localhost:3000, host: 0.0.0.0)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

**Environment Setup:** Create `.env.local` with `GEMINI_API_KEY` (currently configured but not actively used in the codebase).

## Architecture

### File Structure
This is a flat structure with all source files at the root level:
- `App.tsx` - Main application component (~58KB, contains all views and components)
- `types.ts` - TypeScript interfaces and enums (data models)
- `constants.ts` - Mock data for development
- `index.tsx` - React entry point
- `vite.config.ts` - Build configuration with path aliases (`@/*` → root)

**Important:** The entire UI is currently in a single `App.tsx` file. This is a monolithic structure that needs refactoring.

### Component Structure

The app has three main views (state-based, not URL routing):

1. **DashboardOverview** (`view === 'dashboard'`)
   - Top metrics cards (total conversations, sentiment score, urgent issues)
   - KeywordAnalysisPanel with donut chart (category distribution) and bar chart (top keywords)
   - Time range filtering (7d, 15d, 30d, 90d, 1y)
   - Priority Attention Board table (actionable customers)
   - Sentiment Trend line chart (7-day tracking)
   - Intent Distribution radar chart
   - Peak Hours bar chart

2. **ChatAnalysis** (`view === 'chat'`)
   - User search sidebar (filter by nickname)
   - 360° Customer Profile view with:
     - AI Persona Analysis (summary, interests, pain points)
     - Recommended Actions (AI sales suggestions)
     - Financial metrics (LTV, AOV, discount sensitivity)
     - Intent Distribution radar chart
   - Purchase History table (latest order + full history)
   - Communication view (chat grouped by date, collapsible sections)

3. **SettingsView** (`view === 'settings'`)
   - Pipeline configuration (references Playwright crawler)
   - Database connection (PostgreSQL mentioned)
   - Dictionary management for keyword tagging

### Reusable UI Components
- **NotionCard** - Card container with Notion-style styling
- **NotionTag** - Colored tags with 9 pastel colors (gray, brown, orange, yellow, green, blue, purple, pink, red)

### Design System
Notion-inspired aesthetic:
- Colors: `#F7F7F5` (sidebar), `#E9E9E7` (borders), `#37352F` (text)
- Custom Tailwind config in `index.html` via CDN
- Typography: Serif headers, sans-serif body, SF Mono for data
- Minimal shadows (0 1px 2px), thin borders

## Data Models

Key types from `types.ts`:

- **ChatMessage** - Customer service messages (buyer/seller, timestamps, content)
- **CustomerProfile** - 360° customer data with:
  - Demographics (city, new/existing status)
  - Lifetime metrics (LTV, total orders)
  - Discount analysis (discount_ratio identifies "discount seekers")
  - Recent activity (L6M - last 6 months)
  - Intent scores for radar chart
  - Order history with status
  - AI-powered analysis (summary, interests, pain points, recommended actions)
- **BuyerSession** - Combines profile + messages + sentiment
- **KeywordMetric** - Text frequency with category classification
- **ActionableCustomer** - Priority issues (Churn Risk, Negative Review, Stockout Request, Gift Inquiry, High Value)
- **IntentType enum** - Pre-sale, Post-sale, Logistics, Usage Guide, Complaint
- **SentimentType enum** - Positive, Neutral, Negative

## Technology Stack

- **React 19.2.3** with TypeScript 5.8.2
- **Vite 6.2.0** as build tool
- **Recharts 3.6.0** for data visualization (Line, Bar, Pie, Radar charts)
- **Lucide React 0.562.0** for icons
- **Tailwind CSS** via CDN (not npm)

## Related Projects

**chat-history-crawler** (`d:\Work\ai\projects\chat-history-crawler`) is a Python Playwright-based scraper that:
- Crawls chat history from Qianniu Workbench (Taobao/Tmall customer service platform)
- Intercepts network responses to extract chat data
- Stores data in PostgreSQL database
- This dashboard is designed to visualize data from that crawler

The crawler uses:
- Playwright for browser automation
- PostgreSQL for data storage
- Network response interception for data extraction

## Current State

**Working:**
- Full UI with mock data
- All charts and visualizations
- Customer 360° profile view
- Chat history display with date grouping
- Time range filtering (UI only)

**Not Yet Implemented:**
- Real API integration (Gemini API key configured but unused)
- Backend connectivity (PostgreSQL)
- Real data fetching from crawler database
- URL routing (uses state-based view switching)
- Authentication
- Export functionality (CSV mentioned in UI)

**Known Issues:**
- Monolithic `App.tsx` file needs to be split into separate components
- No testing framework
- No error boundaries
- No loading states for async operations

## Key Integration Points

When implementing real data connectivity:
1. **Gemini API** - For AI-powered customer analysis (customer summaries, recommended actions)
2. **PostgreSQL** - For storing and fetching chat data, customer profiles
3. **Playwright Crawler** - The `chat-history-crawler` project populates the database

The data flow should be:
```
Qianniu Workbench → Playwright Crawler → PostgreSQL → This Dashboard
```

## Build Configuration

- Port: 3000, Host: 0.0.0.0 (network accessible)
- Path alias: `@/*` maps to root directory
- Environment variables injected via `define:` in vite.config.ts
- TypeScript strict mode enabled
- JSX: react-jsx (automatic runtime)
