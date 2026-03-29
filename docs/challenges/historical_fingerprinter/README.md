# Historical Fingerprinter Challenge

## Overview

The **Historical Fingerprinter** challenge tests miners' ability to develop an SDK that can fingerprint browser metrics and link spoofed data to existing entries in a SQLite database. The challenge evaluates how well miners can process raw browser fingerprinting data collected using CreepJS and identify unique visitor characteristics.

Miners must demonstrate the ability to preprocess raw metrics, generate unique fingerprints, and maintain a historical database that can link new submissions to previously seen visitors.

## Challenge Flow

1. **Data Collection**: Browser metrics are collected using official CreepJS
2. **Submission**: Miners submit three Python files containing their SDK implementation
3. **Processing**: The system sends browser metrics one by one to the miner's SDK
4. **Fingerprinting**: Miner must preprocess the metrics and generate a unique fingerprint
5. **Linking**: If the data appears spoofed, the miner must link it to already existing data in the SQLite database

## General Technical Requirements

- **Development Language**: Python
- **Operating System**: Ubuntu 24.04
- **Environment**: Docker container environment
- **Architecture**: amd64 (ARM64 at your own risk)

## General Guidelines

- **Database**: SQLite with SQLAlchemy support
- **Data Source**: CreepJS browser metrics (official collection)
- **Processing**: Each request must be handled within 0.5 seconds

## Pre-installed Packages

The following packages are pre-installed in the challenge environment:

- `sqlalchemy` - Database ORM
- `math` - Mathematical utilities
- `fastapi` - Web framework
- `pydantic` - Data validation
- `sqlite3` - SQLite database (built-in)
- Standard library modules (`hashlib`, `json`, `logging`, `typing`)

Miners **cannot install any additional packages**. All required functionality must be implemented using the pre-installed packages and Python standard library.

## Code Structure Requirements

Miners must submit exactly **three Python files** with specific function names:

### Required Functions

Miners have full flexibility to define their own database schema and implementation within these functions. The only requirement is that the following three function names must exist in the submission scripts:

1. **`initialize_db(db_path: str | None = None) -> sqlite3.Connection`**
   - Initializes the SQLite database connection
   - Creates database tables (miners can define their own schema)
   - Returns a connection object

2. **`preprocess_metrics(raw_metrics: dict[str, Any]) -> dict[str, Any]`**
   - Takes raw CreepJS browser metrics as input
   - Extracts and normalizes relevant fingerprinting fields
   - Returns a cleaned dictionary of metrics

3. **`generate_and_link(payload: dict[str, Any], db_conn: sqlite3.Connection) -> dict[str, Any]`**
   - Generates a unique fingerprint from the processed metrics
   - Checks if the fingerprint already exists in the database
   - Inserts new fingerprints or updates existing entries
   - Returns a dictionary with `fingerprint`, `is_new` flag, and optionally `id`

### Line Limit

- Each file is limited to a maximum of **1000 lines**

## Fingerprinting Fields

The following browser metrics are collected and should be processed:

| Category | Fields |
|----------|--------|
| Canvas | `canvas_geometry`, `canvas_text`, `canvas_winding` |
| WebGL | `gpu_renderer`, `gpu_vendor` |
| Fonts | `fonts`, `font_preferences` |
| Screen | `screen_resolution`, `color_depth`, `screen_frame` |
| Navigator | `languages`, `platform`, `vendor`, `vendor_flavors`, `hardware_concurrency`, `device_memory` |
| System | `architecture`, `cpu_class`, `os_cpu`, `timezone` |
| Browser | `browser_name`, `browser_version` |
| Storage | `cookies_enabled`, `local_storage`, `session_storage`, `indexed_db`, `open_database` |
| Audio | `audio_hash` |
| Other | `math_signature`, `plugins_count`, `max_touch_points`, `hdr`, `contrast`, `forced_colors`, `inverted_colors`, `monochrome`, `reduced_motion`, `pdf_viewer_enabled` |

## Database Schema

Miners can define their own database schema within the `initialize_db` function. Below is an example schema for reference:

```sql
CREATE TABLE IF NOT EXISTS fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,
    visitor_id TEXT,
    user_agent TEXT,
    ip_address TEXT,
    architecture TEXT,
    canvas_geometry TEXT,
    canvas_text TEXT,
    canvas_winding INTEGER,
    audio_hash TEXT,
    color_depth INTEGER,
    color_gamut TEXT,
    contrast INTEGER,
    cookies_enabled INTEGER,
    cpu_class TEXT,
    device_memory INTEGER,
    fonts TEXT,
    font_preferences TEXT,
    forced_colors INTEGER,
    hardware_concurrency INTEGER,
    hdr INTEGER,
    indexed_db INTEGER,
    inverted_colors INTEGER,
    languages TEXT,
    local_storage INTEGER,
    math_signature TEXT,
    monochrome INTEGER,
    open_database INTEGER,
    os_cpu TEXT,
    os TEXT,
    pdf_viewer_enabled INTEGER,
    platform TEXT,
    plugins_count INTEGER,
    reduced_motion INTEGER,
    screen_frame TEXT,
    screen_resolution TEXT,
    session_storage INTEGER,
    timezone TEXT,
    max_touch_points INTEGER,
    vendor TEXT,
    vendor_flavors TEXT,
    gpu_renderer TEXT,
    gpu_vendor TEXT,
    browser_name TEXT,
    browser_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## API Endpoint

The challenge exposes a single endpoint:

```
POST /fingerprint
```

**Request Body:**
```json
{
    "products": {
        "canvas2d": { ... },
        "canvasWebgl": { ... },
        "font": { ... },
        "screen": { ... },
        "navigator": { ... },
        "timezone": { ... },
        ...
    }
}
```

**Response:**
```json
{
    "fingerprint": "sha256_hash_here",
    "is_new": true
}
```

## Example Usage

```python
# Initialize database
db_conn = initialize_db()

# Preprocess raw metrics
processed = preprocess_metrics(raw_creepjs_data)

# Generate fingerprint and link to database
result = generate_and_link(processed, db_conn)

print(result)
# Output: {'fingerprint': 'abc123...', 'is_new': True, 'id': 1}
```

## Submission Path

**Dedicated Path:** `templates/commit/src/fingerprinter/src/submissions/`

Place your three Python files in this directory:

- `initializer.py` - Contains `initialize_db` function
- `metrics_collector.py` - Contains `preprocess_metrics` function
- `linker.py` - Contains `generate_and_link` function

## Performance Requirements

- **Time Limit**: Each request must complete within **0.5 seconds**
- **Memory**: Efficient memory usage for large-scale fingerprinting operations

## Plagiarism Check

We maintain strict originality standards:

- All submissions are compared against other miners' SDKs
- 100% similarity = zero score
- Similarity above 60% will result in rejection of the submission

## Challenge Versions

**Current:**

- [**v1** (Active)](./v1.md) - Hardware fingerprinting baseline with weighted scoring

## Resources & Guides

- [Building a Submission Commit](../../miner/workflow/3.build-and-publish.md) - General submission instructions
- [Challenge Repository](https://github.com/RedTeamSubnet/historical-fingerprinter-challenge/)
- [Miner Repository](https://github.com/RedTeamSubnet/miner/)
- [CreepJS Documentation](https://github.com/Abel666999/CreepJS)

## References

- Docker - <https://docs.docker.com>
- SQLite - <https://www.sqlite.org/docs.html>
- SQLAlchemy - <https://www.sqlalchemy.org/>
- FastAPI - <https://fastapi.tiangolo.com>
