# doofinder-mcp

MCP server for Doofinder — connects Claude Desktop to the Doofinder Stats API so you can query your store's search analytics in plain language.

## What you can ask

- Top searched phrases and queries with no results
- Daily searches, clicks, sessions and checkouts over any date range
- Most clicked products
- Top selling items
- Search engine usage summary (visits, sessions, searches)

## Requirements

- Python 3.10+
- Claude Desktop
- Doofinder account with API access

## Installation

1. Clone the repository:

```bash
   git clone https://github.com/heredero7/doofinder-mcp.git
   cd doofinder-mcp
```

2. Install dependencies:

```bash
   pip install -r requirements.txt
```

3. Get your credentials from the Doofinder Admin Panel:
   - **API Key** → Account → API Keys
   - **Hash ID** → Configuration → Search Engines

4. Add the server to your Claude Desktop config (`claude_desktop_config.json`):

```json
   {
     "mcpServers": {
       "doofinder": {
         "command": "python",
         "args": ["/path/to/doofinder_mcp.py"],
         "env": {
           "DOOFINDER_API_KEY": "your-api-key",
           "DOOFINDER_HASHID": "your-hashid"
         }
       }
     }
   }
```

5. Restart Claude Desktop.

## Usage

Once connected, ask Claude in natural language:

> "Show me the top 10 searches from last week"  
> "Compare clicks this week vs last week"  
> "What searches returned no results in June?"  
> "Which products were clicked most in the last 30 days?"

## Tools

| Tool | Description |
|------|-------------|
| `get_top_searches` | Most frequent search queries |
| `get_searches_over_time` | Daily search volume |
| `get_sessions_over_time` | Daily session counts |
| `get_clicks_over_time` | Daily click counts |
| `get_checkouts_over_time` | Daily checkout counts |
| `get_top_clicked_items` | Most clicked products |
| `get_search_engine_usage` | Visits, sessions and searches summary |
| `get_top_sales` | Top selling items |
| `get_no_result_searches` | Queries that returned zero results |
| `get_popular_searches` | Searches with the most clicked results |

## Notes

- All dates use `YYYYMMDD` format internally — Claude converts your natural language dates automatically.
- Data is scoped to the EU1 zone. If your store is on `us1`, update `BASE_URL` in `doofinder_mcp.py`.
- Stats availability depends on your Doofinder plan and whether click/checkout events are being sent.
