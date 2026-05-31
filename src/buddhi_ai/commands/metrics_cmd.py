import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from buddhi_ai.metrics.constants import INPUT_PRICE_PER_MTOK, PRICING_LABEL, TOKEN_ENCODING
from buddhi_ai.metrics.db import init_metrics_db, get_metrics_db_path

# ANSI escape codes for coloring
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

def _format_number(n: int | float) -> str:
    """Format large numbers with K/M suffixes."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))

def _print_sparkline(data: list[int]) -> str:
    """Generate a simple ascii sparkline."""
    if not data:
        return ""
    bars = " ▂▃▄▅▆▇█"
    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val
    if range_val == 0:
        return bars[0] * len(data)
    return "".join(bars[int((x - min_val) / range_val * 7)] for x in data)

def handle_metrics(args: argparse.Namespace) -> None:
    """Main handler for the `buddhi metrics` command."""
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
            
    db_path = get_metrics_db_path()
    
    if args.reset:
        if db_path.exists():
            conn = init_metrics_db()
            conn.execute("DELETE FROM tool_events")
            conn.commit()
            conn.close()
            print(f"{GREEN}Successfully reset all metrics data.{RESET}")
        else:
            print(f"{YELLOW}No metrics data found to reset.{RESET}")
        return

    if not db_path.exists():
        if args.json:
            print("{}")
        else:
            print(f"{YELLOW}No metrics data found. Run some MCP tools first!{RESET}")
        return

    conn = init_metrics_db()
    cursor = conn.cursor()
    
    cutoff_time = (datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp()

    # Base query for the requested time window
    cursor.execute(
        """
        SELECT 
            tool_name,
            COUNT(*) as total_calls,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_calls,
            AVG(duration_ms) as avg_duration,
            SUM(tokens_saved) as total_tokens_saved
        FROM tool_events
        WHERE timestamp_unix >= ?
        GROUP BY tool_name
        ORDER BY total_calls DESC
        """,
        (cutoff_time,)
    )
    tool_stats = cursor.fetchall()
    
    if not tool_stats and not args.json:
        print(f"{YELLOW}No metrics data found for the last {args.days} days.{RESET}")
        return

    # Calculate totals
    total_calls = sum(row[1] for row in tool_stats)
    total_successes = sum(row[2] for row in tool_stats)
    total_saved = sum(row[4] or 0 for row in tool_stats)
    total_success_rate = (total_successes / total_calls * 100) if total_calls > 0 else 0
    money_saved = (total_saved / 1_000_000) * INPUT_PRICE_PER_MTOK

    # Fetch daily activity for sparkline
    cursor.execute(
        """
        SELECT 
            date(datetime(timestamp_unix, 'unixepoch')) as day,
            COUNT(*) as calls
        FROM tool_events
        WHERE timestamp_unix >= ?
        GROUP BY day
        ORDER BY day ASC
        """,
        (cutoff_time,)
    )
    daily_stats = cursor.fetchall()
    sparkline_data = [row[1] for row in daily_stats]
    
    # Fetch recent errors
    cursor.execute(
        """
        SELECT timestamp_iso, tool_name, error_message
        FROM tool_events
        WHERE status = 'error' AND timestamp_unix >= ?
        ORDER BY timestamp_unix DESC
        LIMIT 5
        """,
        (cutoff_time,)
    )
    recent_errors = cursor.fetchall()
    
    conn.close()

    if args.json:
        # JSON Output
        output = {
            "period_days": args.days,
            "total_calls": total_calls,
            "success_rate_pct": total_success_rate,
            "tokens_saved": total_saved,
            "estimated_savings_usd": money_saved,
            "tools": [
                {
                    "name": row[0],
                    "calls": row[1],
                    "success_rate_pct": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    "avg_duration_ms": row[3],
                    "tokens_saved": row[4] or 0,
                    "estimated_savings_usd": ((row[4] or 0) / 1_000_000) * INPUT_PRICE_PER_MTOK
                }
                for row in tool_stats
            ],
            "recent_errors": [
                {
                    "timestamp": row[0],
                    "tool": row[1],
                    "error": row[2]
                }
                for row in recent_errors
            ]
        }
        print(json.dumps(output, indent=2))
        return

    # Terminal Dashboard Output
    print(f"\n{BOLD}{CYAN}🚀 buddhi-ai Tool Usage Metrics{RESET} {DIM}(Last {args.days} days){RESET}\n")
    
    # Summary Bar
    print(f"  {BOLD}Total Calls:{RESET} {total_calls}   |   ", end="")
    print(f"{BOLD}Success Rate:{RESET} {GREEN if total_success_rate > 90 else YELLOW}{total_success_rate:.1f}%{RESET}   |   ", end="")
    print(f"{BOLD}Tokens Saved:{RESET} ~{_format_number(total_saved)}   |   ", end="")
    print(f"{BOLD}Est. Saved:{RESET} {GREEN}${money_saved:.2f}{RESET}\n")

    # Table Header
    print(f"{DIM}┌─────────────────┬───────┬──────────┬──────────────┬──────────────┬───────────────┐{RESET}")
    print(f"{DIM}│{RESET} {BOLD}Tool            {RESET}{DIM}│{RESET} {BOLD}Calls{RESET} {DIM}│{RESET} {BOLD}Success%{RESET} {DIM}│{RESET} {BOLD}Avg Duration{RESET} {DIM}│{RESET} {BOLD}Tokens Saved{RESET} {DIM}│{RESET} {BOLD}Est. Saved ($){RESET}{DIM}│{RESET}")
    print(f"{DIM}├─────────────────┼───────┼──────────┼──────────────┼──────────────┼───────────────┤{RESET}")
    
    for row in tool_stats:
        t_name = row[0][:15].ljust(15)
        t_calls = str(row[1]).rjust(5)
        t_success = f"{(row[2] / row[1] * 100):.1f}%".rjust(8) if row[1] > 0 else "0.0%".rjust(8)
        t_dur = f"{row[3]:.0f}ms".rjust(12) if row[3] else "-".rjust(12)
        t_saved = f"~{_format_number(row[4] or 0)}".rjust(12)
        t_money = f"${(((row[4] or 0) / 1_000_000) * INPUT_PRICE_PER_MTOK):.2f}".rjust(13)
        
        # Colorize success rate
        succ_val = (row[2] / row[1] * 100) if row[1] > 0 else 0
        if succ_val > 95:
            t_success = f"{GREEN}{t_success}{RESET}"
        elif succ_val > 80:
            t_success = f"{YELLOW}{t_success}{RESET}"
        else:
            t_success = f"{RED}{t_success}{RESET}"

        print(f"{DIM}│{RESET} {CYAN}{t_name}{RESET} {DIM}│{RESET} {t_calls} {DIM}│{RESET} {t_success} {DIM}│{RESET} {t_dur} {DIM}│{RESET} {t_saved} {DIM}│{RESET} {GREEN}{t_money}{RESET} {DIM}│{RESET}")
    
    print(f"{DIM}└─────────────────┴───────┴──────────┴──────────────┴──────────────┴───────────────┘{RESET}\n")

    if sparkline_data:
        print(f"  {BOLD}Activity Sparkline:{RESET} {CYAN}{_print_sparkline(sparkline_data)}{RESET}\n")

    if recent_errors:
        print(f"  {BOLD}{RED}Recent Errors:{RESET}")
        for err in recent_errors:
            # Shorten timestamp and error
            ts = err[0][:16].replace('T', ' ')
            msg = err[2][:80] + "..." if len(err[2]) > 80 else err[2]
            print(f"  {DIM}[{ts}]{RESET} {YELLOW}{err[1]}{RESET}: {msg}")
        print()

    # Footer
    print(f"{DIM}⚠ Token counts are approximate (~{TOKEN_ENCODING} encoding).{RESET}")
    print(f"{DIM}  Cost estimates are approximate and based on {PRICING_LABEL} pricing (${INPUT_PRICE_PER_MTOK:.2f}/MTok input).{RESET}\n")
