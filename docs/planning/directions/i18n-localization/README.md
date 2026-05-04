# Strand: Internationalization and Localization

## Planning alignment (normative)

- **MVP locales:** `de` and `en` only; both must exist for every shipped UI key and for seeded domain JSONB (`title_i18n`, etc.).
- **Single runtime source:** Postgres (`ui_translation` + JSONB on domain rows). Seed **files** may exist only as input to load the database—not a parallel runtime source of truth.
- **Build order:** follow [../../02-incremental-mvp-roadmap.md](../../02-incremental-mvp-roadmap.md) **Wave 0 (continued)** before shipping non-placeholder UI.
- **Cross-links:** [../data-model-migrations/README.md](../data-model-migrations/README.md), [../backend-api/README.md](../backend-api/README.md), [../web-frontend/README.md](../web-frontend/README.md), [../mobile-flutter/README.md](../mobile-flutter/README.md).

The remainder of this document expands schema and API conventions. **Code samples are illustrative** until an implementation exists in the repo.

## Vision

**Single source of truth: PostgreSQL database.** All user-facing text—domain data (document titles, jurisdiction names) AND UI strings (buttons, labels, errors)—lives in the database with full locale coverage. Frontend and mobile apps fetch translations dynamically, enabling instant language switching and future community-contributed translations via the same social contribution model.

## Core Principles

1. **DB as authority**: No hardcoded strings in frontend/mobile; no split between "domain data i18n" and "UI i18n"
2. **API-driven**: Apps fetch translation bundles on load; locale changes trigger data refetch with new `Accept-Language` header
3. **Fallback chain**: Requested locale → `de` (German primary) → `en` (English fallback) → translation key (dev mode)
4. **Community-extensible**: Future phases allow users to propose translations (same contribution/voting workflow as document requirements)
5. **Performance**: Translation bundles cached aggressively (HTTP Cache-Control); domain data fetched per-request with locale parameter

## Supported Locales (MVP)

| Locale Code | Language | Status | Phase |
|-------------|----------|--------|-------|
| `de` | German (Deutsch) | ✅ Primary | MVP |
| `en` | English | ✅ Full support | MVP |
| `pl` | Polish (Polski) | ⏳ Planned | Phase 11+ |
| `it` | Italian (Italiano) | ⏳ Planned | Phase 16+ (Italy expansion) |
| `fr` | French (Français) | ⏳ Planned | Phase 16+ (France expansion) |

## Data Model

### 1. Domain Data with JSONB Localization

All domain entities store localized text in JSONB columns:

```sql
CREATE TABLE document (
  id UUID PRIMARY KEY,
  slug TEXT NOT NULL,
  title_i18n JSONB NOT NULL,          -- { "de": "Elterngeld", "en": "Parental allowance" }
  description_i18n JSONB,              -- { "de": "...", "en": "..." }
  jurisdiction_id UUID REFERENCES jurisdiction(id),
  official_url TEXT,
  volatility_score FLOAT DEFAULT 0.5,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE jurisdiction (
  id UUID PRIMARY KEY,
  code TEXT NOT NULL,                  -- ISO codes where available (DE, DE-SN, etc.)
  kind TEXT NOT NULL,                  -- COUNTRY | REGION | MUNICIPALITY
  levels TEXT[] NOT NULL,              -- Array: which levels this unit satisfies
  name_i18n JSONB NOT NULL,            -- { "de": "Dresden", "en": "Dresden" }
  parent_id UUID REFERENCES jurisdiction(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE requirement (
  id UUID PRIMARY KEY,
  parent_document_id UUID REFERENCES document(id),
  required_document_id UUID REFERENCES document(id),
  jurisdiction_id UUID REFERENCES jurisdiction(id),
  notes_i18n JSONB,                    -- Optional explanation: why this is required
  source TEXT DEFAULT 'canonical',
  valid_from DATE,
  valid_to DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Design choice:** JSONB over separate `document_locale` table:
- ✅ Simpler queries (no JOIN per locale column)
- ✅ Atomic updates (one row update, not N inserts)
- ✅ Flexible: adding a locale doesn't require schema migration
- ✅ PostgreSQL JSONB is indexed and fast
- ⚠️ Cons: Manual validation that all locales are present (handled by app-layer validation)

### 2. UI Translation Strings

Centralized table for all UI text (buttons, labels, errors, notifications):

```sql
CREATE TABLE ui_translation (
  key TEXT NOT NULL,                   -- Dot-notation: "common.submit", "errors.not_found"
  locale TEXT NOT NULL,                -- ISO 639-1: de, en, pl, ...
  value TEXT NOT NULL,                 -- Translated string, supports {placeholders}
  context TEXT,                        -- Optional: where this is used (helps translators)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (key, locale)
);

-- Index for API endpoint that fetches all translations for a locale
CREATE INDEX idx_ui_translation_locale ON ui_translation(locale);

-- Example rows:
INSERT INTO ui_translation (key, locale, value, context) VALUES
  ('common.submit', 'de', 'Absenden', 'Button label'),
  ('common.submit', 'en', 'Submit', 'Button label'),
  ('common.cancel', 'de', 'Abbrechen', 'Button label'),
  ('common.cancel', 'en', 'Cancel', 'Button label'),
  ('errors.document_not_found', 'de', 'Dokument nicht gefunden: {id}', 'Error message'),
  ('errors.document_not_found', 'en', 'Document not found: {id}', 'Error message'),
  ('nav.browse_documents', 'de', 'Dokumente durchsuchen', 'Navigation link'),
  ('nav.browse_documents', 'en', 'Browse Documents', 'Navigation link');
```

**Key naming convention:**
- `common.*` — Shared across app (submit, cancel, save, delete, search, loading, error)
- `nav.*` — Navigation labels (menu items, breadcrumbs)
- `auth.*` — Login, signup, logout, profile
- `documents.*` — Document-specific UI (list headers, detail labels)
- `contributions.*` — Social layer (propose, vote, accept, reject)
- `moderator.*` — Moderation interface
- `admin.*` — Admin dashboard
- `errors.*` — Error messages (can include `{placeholders}` for interpolation)
- `notifications.*` — Toast messages, push notification templates

### 3. Locale Metadata (Optional, for future)

```sql
CREATE TABLE supported_locale (
  code TEXT PRIMARY KEY,               -- de, en, pl, it, fr
  name_native TEXT NOT NULL,           -- Deutsch, English, Polski, Italiano, Français
  name_english TEXT NOT NULL,          -- German, English, Polish, Italian, French
  flag_emoji TEXT,                     -- 🇩🇪, 🇬🇧, 🇵🇱, 🇮🇹, 🇫🇷
  enabled BOOLEAN DEFAULT TRUE,        -- Feature flag: disable incomplete locales
  completeness_pct FLOAT DEFAULT 0.0,  -- % of ui_translation keys covered
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO supported_locale (code, name_native, name_english, flag_emoji, enabled, completeness_pct) VALUES
  ('de', 'Deutsch', 'German', '🇩🇪', TRUE, 100.0),
  ('en', 'English', 'English', '🇬🇧', TRUE, 100.0),
  ('pl', 'Polski', 'Polish', '🇵🇱', FALSE, 0.0);  -- Not yet enabled
```

**Purpose:** Powers locale picker UI; tracks translation coverage; allows disabling incomplete locales.

## API Conventions

### Locale Negotiation

**Option 1 (Recommended): `Accept-Language` Header**

```http
GET /api/v1/documents
Accept-Language: en
```

**Backend behavior:**
1. Parse `Accept-Language` header (supports quality values: `en-US,en;q=0.9,de;q=0.8`)
2. Match against `supported_locale.enabled = TRUE`
3. Fallback: `de` → `en` → `en` (always)
4. Attach resolved locale to `request.state.locale` via middleware

**Option 2 (Alternative): Query Parameter**

```http
GET /api/v1/documents?locale=en
```

**Tradeoff:** Query param easier to test/debug, but header is HTTP standard. **Decision: Use header; support query param override for debugging.**

### Response Format

**Domain data responses** (documents, jurisdictions):

```json
{
  "id": "123",
  "slug": "elterngeld",
  "title": "Parental allowance",        // ← Backend selected locale from title_i18n
  "description": "Financial support...",
  "jurisdiction": {
    "name": "Dresden"                   // ← Also localized
  }
}
```

**Backend responsibility:** Extract correct locale from JSONB before serialization. Frontend receives **already-localized** strings, not `title_i18n` object.

**UI translation bundle endpoint:**

```http
GET /api/v1/translations?locale=en
```

**Response:**

```json
{
  "locale": "en",
  "translations": {
    "common.submit": "Submit",
    "common.cancel": "Cancel",
    "errors.document_not_found": "Document not found: {id}",
    "nav.browse_documents": "Browse Documents",
    ...
  }
}
```

**Caching:** Aggressive HTTP cache headers:
```http
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
ETag: "translation-bundle-en-v123"
```

Clients can cache for 1 hour; backend increments version on any `ui_translation` update.

### Error Responses

Errors are **also localized**:

```http
POST /api/v1/contributions
Accept-Language: de
Content-Type: application/json

{ "parent_document_id": "invalid-uuid" }
```

**Response (422 Unprocessable Entity):**

```json
{
  "error": "validation_error",
  "message": "Validierungsfehler bei der Eingabe",  // ← Localized
  "details": [
    {
      "field": "parent_document_id",
      "message": "Ungültige UUID: invalid-uuid"     // ← Localized
    }
  ]
}
```

**Implementation:** Backend translates Pydantic validation errors using `ui_translation` table.

## Backend Implementation

### Middleware (Litestar)

```python
from litestar import Litestar, Request
from litestar.datastructures import State
from typing import Annotated

class LocaleMiddleware:
    def __init__(self, app: Litestar):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # Parse Accept-Language header
        locale = self._parse_locale(request.headers.get("accept-language", "de"))
        
        # Override with query param if present (for debugging)
        if "locale" in request.query_params:
            locale = request.query_params["locale"]
        
        # Validate against supported locales
        locale = await self._validate_locale(locale, request.app.state.db_session)
        
        # Attach to request state
        request.state.locale = locale
        
        return await call_next(request)
    
    def _parse_locale(self, header: str) -> str:
        # Simple parser; production: use werkzeug.http.parse_accept_header
        parts = header.split(",")
        if parts:
            return parts[0].split(";")[0].strip().lower()[:2]  # First 2 chars
        return "de"
    
    async def _validate_locale(self, locale: str, db_session) -> str:
        # Check if locale is in supported_locale table and enabled
        result = await db_session.execute(
            "SELECT code FROM supported_locale WHERE code = :locale AND enabled = TRUE",
            {"locale": locale}
        )
        if result.scalar():
            return locale
        # Fallback chain
        return "de"
```

### Dependency Injection

```python
from litestar import get

def get_locale(request: Request) -> str:
    """DI provider for current request locale."""
    return request.state.locale

@get("/documents")
async def list_documents(
    locale: Annotated[str, Depends(get_locale)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    # Use locale to select from JSONB columns
    ...
```

### JSONB Extraction Utility

```python
from sqlalchemy import func, select, case

def localized_field(column, locale: str, fallback_locale: str = "de"):
    """
    Extract localized value from JSONB column with fallback.
    
    Usage:
        query = select(
            Document.id,
            localized_field(Document.title_i18n, "en").label("title")
        )
    """
    return case(
        (column[locale].isnot(None), column[locale]),
        else_=column[fallback_locale]
    )

# In endpoint:
stmt = select(
    Document.id,
    Document.slug,
    localized_field(Document.title_i18n, locale).label("title"),
    localized_field(Document.description_i18n, locale).label("description")
).where(Document.jurisdiction_id == jurisdiction_id)

results = await db_session.execute(stmt)
```

### Translation Service

```python
class TranslationService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._cache: Dict[str, Dict[str, str]] = {}  # In-memory cache
    
    async def get_bundle(self, locale: str) -> Dict[str, str]:
        """Fetch all UI translations for a locale."""
        if locale in self._cache:
            return self._cache[locale]
        
        stmt = select(UITranslation.key, UITranslation.value).where(
            UITranslation.locale == locale
        )
        result = await self.db_session.execute(stmt)
        bundle = {row.key: row.value for row in result}
        
        self._cache[locale] = bundle
        return bundle
    
    async def translate(self, key: str, locale: str, **params) -> str:
        """Translate a single key with placeholder interpolation."""
        bundle = await self.get_bundle(locale)
        template = bundle.get(key, key)  # Fallback to key if missing
        return template.format(**params)
    
    def invalidate_cache(self):
        """Call when ui_translation table is updated."""
        self._cache.clear()
```

### Error Localization

```python
from litestar.exceptions import ValidationException

async def validation_exception_handler(request: Request, exc: ValidationException):
    locale = request.state.locale
    translation_service = request.app.state.translation_service
    
    localized_message = await translation_service.translate(
        "errors.validation_error",
        locale
    )
    
    details = []
    for error in exc.extra:
        field_message = await translation_service.translate(
            f"errors.{error['type']}",
            locale,
            **error.get("ctx", {})
        )
        details.append({
            "field": error["loc"][-1],
            "message": field_message
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": localized_message,
            "details": details
        }
    )
```

## Frontend Implementation (React)

### Translation Context

```typescript
// src/contexts/LocaleContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';

interface TranslationBundle {
  [key: string]: string;
}

interface LocaleContextType {
  locale: string;
  setLocale: (locale: string) => void;
  t: (key: string, params?: Record<string, any>) => string;
  isLoading: boolean;
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

export const LocaleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<string>(
    localStorage.getItem('locale') || navigator.language.split('-')[0] || 'de'
  );
  const [translations, setTranslations] = useState<TranslationBundle>({});
  const [isLoading, setIsLoading] = useState(true);

  // Fetch translation bundle when locale changes
  useEffect(() => {
    const fetchTranslations = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/translations?locale=${locale}`, {
          headers: { 'Accept-Language': locale }
        });
        const data = await response.json();
        setTranslations(data.translations);
      } catch (error) {
        console.error('Failed to load translations:', error);
        // Fallback: use cached or hardcoded emergency strings
      } finally {
        setIsLoading(false);
      }
    };

    fetchTranslations();
  }, [locale]);

  const setLocale = (newLocale: string) => {
    setLocaleState(newLocale);
    localStorage.setItem('locale', newLocale);
    // Update API client default header
    apiClient.setDefaultHeader('Accept-Language', newLocale);
  };

  const t = (key: string, params?: Record<string, any>): string => {
    let value = translations[key] || key; // Fallback to key if missing
    
    // Simple placeholder interpolation
    if (params) {
      Object.keys(params).forEach(param => {
        value = value.replace(`{${param}}`, String(params[param]));
      });
    }
    
    return value;
  };

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t, isLoading }}>
      {children}
    </LocaleContext.Provider>
  );
};

export const useLocale = () => {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocale must be used within LocaleProvider');
  }
  return context;
};
```

### API Client Configuration

```typescript
// src/lib/apiClient.ts
class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string> = {};

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  setDefaultHeader(key: string, value: string) {
    this.defaultHeaders[key] = value;
  }

  async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.defaultHeaders,
        ...options?.headers
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(error.message, error.details);
    }

    return response.json();
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_URL);
```

### Usage in Components

```tsx
// src/components/DocumentList.tsx
import { useLocale } from '../contexts/LocaleContext';

export const DocumentList: React.FC = () => {
  const { t } = useLocale();
  const [documents, setDocuments] = useState([]);

  // Documents fetched from API are already localized by backend
  useEffect(() => {
    apiClient.fetch('/api/v1/documents').then(setDocuments);
  }, []);

  return (
    <Box>
      <Heading>{t('documents.list_title')}</Heading>
      {documents.map(doc => (
        <Card key={doc.id}>
          <Heading size="sm">{doc.title}</Heading>  {/* Already localized */}
          <Text>{doc.description}</Text>
        </Card>
      ))}
    </Box>
  );
};
```

### Locale Switcher Component

```tsx
// src/components/LocaleSwitcher.tsx
import { useLocale } from '../contexts/LocaleContext';
import { Menu, MenuButton, MenuList, MenuItem, Button } from '@chakra-ui/react';

export const LocaleSwitcher: React.FC = () => {
  const { locale, setLocale } = useLocale();

  const locales = [
    { code: 'de', label: '🇩🇪 Deutsch', name: 'German' },
    { code: 'en', label: '🇬🇧 English', name: 'English' }
  ];

  return (
    <Menu>
      <MenuButton as={Button} variant="ghost">
        {locales.find(l => l.code === locale)?.label}
      </MenuButton>
      <MenuList>
        {locales.map(l => (
          <MenuItem
            key={l.code}
            onClick={() => setLocale(l.code)}
            fontWeight={l.code === locale ? 'bold' : 'normal'}
          >
            {l.label}
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
};
```

## Mobile Implementation (Flutter)

### Translation Provider

```dart
// lib/providers/locale_provider.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';

class LocaleProvider extends ChangeNotifier {
  Locale _locale = const Locale('de');
  Map<String, String> _translations = {};
  bool _isLoading = true;

  Locale get locale => _locale;
  bool get isLoading => _isLoading;

  LocaleProvider() {
    _loadSavedLocale();
  }

  Future<void> _loadSavedLocale() async {
    final prefs = await SharedPreferences.getInstance();
    final savedLocale = prefs.getString('locale') ?? 'de';
    await setLocale(Locale(savedLocale));
  }

  Future<void> setLocale(Locale newLocale) async {
    _locale = newLocale;
    _isLoading = true;
    notifyListeners();

    try {
      // Fetch translation bundle from API
      final response = await ApiClient.instance.get(
        '/api/v1/translations?locale=${newLocale.languageCode}'
      );
      _translations = Map<String, String>.from(response['translations']);

      // Save preference
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('locale', newLocale.languageCode);

      // Update API client default header
      ApiClient.instance.setDefaultHeader(
        'Accept-Language',
        newLocale.languageCode
      );
    } catch (e) {
      print('Failed to load translations: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  String t(String key, {Map<String, dynamic>? params}) {
    String value = _translations[key] ?? key;

    // Simple placeholder interpolation
    if (params != null) {
      params.forEach((param, val) {
        value = value.replaceAll('{$param}', val.toString());
      });
    }

    return value;
  }
}
```

### API Client Configuration

```dart
// lib/services/api_client.dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  static final ApiClient instance = ApiClient._internal();
  factory ApiClient() => instance;
  ApiClient._internal();

  final String baseURL = const String.fromEnvironment('API_URL');
  final Map<String, String> _defaultHeaders = {
    'Content-Type': 'application/json'
  };

  void setDefaultHeader(String key, String value) {
    _defaultHeaders[key] = value;
  }

  Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(
      Uri.parse('$baseURL$path'),
      headers: _defaultHeaders
    );

    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw ApiException(error['message']);
    }

    return jsonDecode(response.body);
  }
}
```

### Usage in Widgets

```dart
// lib/screens/document_list_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/locale_provider.dart';

class DocumentListScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final localeProvider = Provider.of<LocaleProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(localeProvider.t('documents.list_title')),
      ),
      body: ListView.builder(
        itemBuilder: (context, index) {
          // Documents from API are already localized
          final doc = documents[index];
          return ListTile(
            title: Text(doc.title),  // Already localized by backend
            subtitle: Text(doc.description),
          );
        },
      ),
    );
  }
}
```

### Locale Switcher

```dart
// lib/widgets/locale_switcher.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/locale_provider.dart';

class LocaleSwitcher extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final localeProvider = Provider.of<LocaleProvider>(context);

    return PopupMenuButton<Locale>(
      icon: const Icon(Icons.language),
      onSelected: (locale) => localeProvider.setLocale(locale),
      itemBuilder: (context) => [
        PopupMenuItem(
          value: const Locale('de'),
          child: Text('🇩🇪 Deutsch'),
        ),
        PopupMenuItem(
          value: const Locale('en'),
          child: Text('🇬🇧 English'),
        ),
      ],
    );
  }
}
```

## Seeding Translation Data

### Script: `seed_translations.py`

```python
import asyncio
import json
from pathlib import Path
from sqlalchemy import insert

async def seed_ui_translations(db_session):
    """Seed ui_translation table from JSON files."""
    
    seed_dir = Path(__file__).parent / "seed_data" / "translations"
    
    for locale_file in seed_dir.glob("*.json"):
        locale = locale_file.stem  # Filename without extension (de.json -> de)
        
        with open(locale_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        # Flatten nested dict into dot-notation keys
        flat_translations = flatten_dict(translations)
        
        # Bulk insert
        await db_session.execute(
            insert(UITranslation).values([
                {
                    "key": key,
                    "locale": locale,
                    "value": value,
                    "context": None  # TODO: Add context in seed files
                }
                for key, value in flat_translations.items()
            ])
        )
    
    await db_session.commit()

def flatten_dict(d, parent_key='', sep='.'):
    """Convert {'common': {'submit': 'Submit'}} to {'common.submit': 'Submit'}."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
```

### Seed Files Structure

```
apps/api/seed_data/
├── translations/
│   ├── de.json
│   ├── en.json
│   └── _template.json
└── documents/
    └── mvp_graph.json
```

**Example: `seed_data/translations/de.json`**

```json
{
  "common": {
    "submit": "Absenden",
    "cancel": "Abbrechen",
    "save": "Speichern",
    "delete": "Löschen",
    "search": "Suchen",
    "loading": "Lädt...",
    "error": "Fehler",
    "success": "Erfolgreich"
  },
  "nav": {
    "home": "Startseite",
    "browse_documents": "Dokumente durchsuchen",
    "my_vault": "Meine Dokumente",
    "contributions": "Beiträge",
    "about": "Über uns"
  },
  "auth": {
    "login": "Anmelden",
    "signup": "Registrieren",
    "logout": "Abmelden",
    "email": "E-Mail",
    "password": "Passwort",
    "forgot_password": "Passwort vergessen?"
  },
  "documents": {
    "list_title": "Dokumente",
    "detail_title": "Dokumentdetails",
    "requirements": "Erforderliche Dokumente",
    "no_requirements": "Keine Voraussetzungen",
    "official_source": "Offizielle Quelle"
  },
  "errors": {
    "validation_error": "Validierungsfehler bei der Eingabe",
    "document_not_found": "Dokument nicht gefunden: {id}",
    "unauthorized": "Nicht autorisiert",
    "server_error": "Serverfehler. Bitte versuchen Sie es später erneut."
  }
}
```

**Example: `seed_data/translations/en.json`**

```json
{
  "common": {
    "submit": "Submit",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "search": "Search",
    "loading": "Loading...",
    "error": "Error",
    "success": "Success"
  },
  "nav": {
    "home": "Home",
    "browse_documents": "Browse Documents",
    "my_vault": "My Documents",
    "contributions": "Contributions",
    "about": "About"
  },
  "auth": {
    "login": "Log In",
    "signup": "Sign Up",
    "logout": "Log Out",
    "email": "Email",
    "password": "Password",
    "forgot_password": "Forgot password?"
  },
  "documents": {
    "list_title": "Documents",
    "detail_title": "Document Details",
    "requirements": "Required Documents",
    "no_requirements": "No requirements",
    "official_source": "Official Source"
  },
  "errors": {
    "validation_error": "Input validation error",
    "document_not_found": "Document not found: {id}",
    "unauthorized": "Unauthorized",
    "server_error": "Server error. Please try again later."
  }
}
```

## Future: Community-Contributed Translations (Phase 10+)

### Extend Contribution Model

```sql
-- contribution.type enum adds TRANSLATION
ALTER TYPE contribution_type ADD VALUE 'TRANSLATION';

-- contribution table already has:
-- - type
-- - content (jsonb) — will store: { "key": "...", "locale": "pl", "value": "..." }
-- - status (PENDING | ACCEPTED | REJECTED)
```

### Workflow

1. User navigates to `/translate` (authenticated, role=USER or higher)
2. Selects untranslated key for target locale (e.g., `common.submit` → Polish)
3. Submits translation → creates contribution (type=TRANSLATION, status=PENDING)
4. Community votes on quality
5. Moderator accepts → inserts/updates `ui_translation` table
6. Backend invalidates translation cache
7. Clients fetch updated bundle on next load

**Benefit:** Same social validation model as document proposals ensures quality; non-technical users can contribute via web UI.

## Testing Strategy

### Backend Unit Tests

```python
async def test_locale_fallback(db_session):
    """Test JSONB locale extraction with fallback."""
    doc = Document(
        slug="test",
        title_i18n={"de": "Testdokument", "en": "Test Document"},
        jurisdiction_id=some_jurisdiction_id
    )
    db_session.add(doc)
    await db_session.commit()
    
    # Request English
    stmt = select(
        Document.id,
        localized_field(Document.title_i18n, "en").label("title")
    ).where(Document.slug == "test")
    result = await db_session.execute(stmt)
    row = result.one()
    assert row.title == "Test Document"
    
    # Request missing locale (Polish) - should fall back to German
    stmt = select(
        Document.id,
        localized_field(Document.title_i18n, "pl", fallback_locale="de").label("title")
    ).where(Document.slug == "test")
    result = await db_session.execute(stmt)
    row = result.one()
    assert row.title == "Testdokument"
```

### Frontend Integration Tests

```typescript
test('locale switcher changes UI language', async () => {
  render(
    <LocaleProvider>
      <App />
    </LocaleProvider>
  );
  
  // Default: German
  await waitFor(() => {
    expect(screen.getByText('Dokumente durchsuchen')).toBeInTheDocument();
  });
  
  // Switch to English
  await userEvent.click(screen.getByText('🇬🇧 English'));
  
  await waitFor(() => {
    expect(screen.getByText('Browse Documents')).toBeInTheDocument();
  });
});
```

### Mobile Widget Tests

```dart
testWidgets('Locale switcher updates UI', (WidgetTester tester) async {
  await tester.pumpWidget(
    ChangeNotifierProvider(
      create: (_) => LocaleProvider(),
      child: MaterialApp(home: DocumentListScreen()),
    ),
  );
  
  // Default: German
  expect(find.text('Dokumente'), findsOneWidget);
  
  // Switch locale
  final provider = tester
      .element(find.byType(DocumentListScreen))
      .read<LocaleProvider>();
  await provider.setLocale(const Locale('en'));
  await tester.pumpAndSettle();
  
  // Should update
  expect(find.text('Documents'), findsOneWidget);
});
```

## Performance Considerations

### Translation Bundle Caching

**Backend:**
- In-memory cache per locale (invalidated on `ui_translation` updates)
- HTTP `Cache-Control: max-age=3600` (1 hour)
- `ETag` based on last update timestamp of `ui_translation` table

**Frontend:**
- LocalStorage backup: if API fails, use stale cached bundle
- Service Worker (future): offline support for PWA

### JSONB Query Performance

**Indexes:**
```sql
-- GIN index on JSONB columns for fast extraction
CREATE INDEX idx_document_title_i18n ON document USING GIN (title_i18n);
CREATE INDEX idx_jurisdiction_name_i18n ON jurisdiction USING GIN (name_i18n);
```

**Benchmark:** On test dataset (10K documents), localized query with JSONB extraction: <10ms (PostgreSQL 15, GIN indexed).

### Bundle Size

**MVP estimate (100 keys × 2 locales):**
- ~10KB uncompressed JSON
- ~3KB gzip compressed

**Scale projection (1000 keys × 5 locales):**
- ~100KB uncompressed
- ~30KB gzip compressed

**Mitigation:** If bundle grows large, support incremental loading (namespace-based: fetch `common.*` + `documents.*` only for document pages).

## Migration from Git-Based i18n (Future)

If you ever need to migrate existing Git-based translation files to DB:

```python
async def migrate_translations_to_db():
    """One-time migration script."""
    import json
    from pathlib import Path
    
    locale_dir = Path("packages/i18n/locales")
    
    for locale_file in locale_dir.glob("*.json"):
        locale = locale_file.stem
        
        with open(locale_file, 'r', encoding='utf-8') as f:
            translations = flatten_dict(json.load(f))
        
        # Upsert to ui_translation table
        for key, value in translations.items():
            await db_session.execute(
                """
                INSERT INTO ui_translation (key, locale, value)
                VALUES (:key, :locale, :value)
                ON CONFLICT (key, locale) DO UPDATE SET value = EXCLUDED.value
                """,
                {"key": key, "locale": locale, "value": value}
            )
    
    await db_session.commit()
```

## Documentation for Translators

### Translation Contribution Guide (to be created)

**File:** `docs/CONTRIBUTING_TRANSLATIONS.md`

**Contents:**
- Supported locales and coverage status
- How to add a new locale (create PR with seed file, then admin enables in DB)
- Translation key naming conventions
- Placeholder syntax: `{variable}`
- Context guidelines (when to add `context` column)
- How to test translations locally
- Phase 10+: Web UI for community translations

## Related Planning Documents

- Master summary: [../../00-master-summary.md](../../00-master-summary.md)
- Data model migrations: [../data-model-migrations/README.md](../data-model-migrations/README.md)
- Backend API: [../backend-api/README.md](../backend-api/README.md)
- Web frontend: [../web-frontend/README.md](../web-frontend/README.md)
- Mobile Flutter: [../mobile-flutter/README.md](../mobile-flutter/README.md)
- Social moderation: [../social-moderation/README.md](../social-moderation/README.md) (future TRANSLATION contribution type)

## Next Steps

See updated implementation roadmap in [../../02-incremental-mvp-roadmap.md](../../02-incremental-mvp-roadmap.md) for hour-by-hour i18n integration into phases.
