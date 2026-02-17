#!/usr/bin/env python
"""End-to-End Demo Script for Fraud Detection Multi-Agent System.

This script demonstrates the complete pipeline:
1. Ingest fraud policies into ChromaDB
2. Load synthetic test data (6 transactions)
3. Analyze each transaction sequentially
4. Display formatted results with decision, confidence, and timing
5. Show a complete debate example (pro-fraud vs pro-customer)

Usage:
    uv run python scripts/demo.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.orchestrator import graph
from app.db.engine import async_session as async_session_maker
from app.models import Transaction, CustomerBehavior, OrchestratorState
from app.rag.vector_store import ingest_policies
from app.utils.logger import get_logger, setup_logging
from langchain_core.runnables import RunnableConfig

setup_logging()
logger = get_logger(__name__)
console = Console()


def print_header():
    """Print demo header."""
    title = Text("Fraud Detection Multi-Agent System", style="bold cyan", justify="center")
    subtitle = Text("End-to-End Pipeline Demo", style="dim", justify="center")

    console.print()
    console.print(Panel(
        title + "\n" + subtitle,
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()


def ingest_policies_step():
    """Step 1: Ingest fraud policies into ChromaDB."""
    console.print("[bold cyan]Step 1:[/bold cyan] Ingesting fraud policies into ChromaDB")
    console.print()

    policies_dir = Path(__file__).parent.parent / "policies"

    if not policies_dir.exists():
        console.print(f"[red]✗[/red] Policies directory not found: {policies_dir}")
        console.print("[yellow]⚠[/yellow]  Skipping policy ingestion (may affect RAG results)")
        console.print()
        return 0

    try:
        with console.status("[cyan]Loading policy documents...", spinner="dots"):
            count = ingest_policies(str(policies_dir))

        console.print(f"[green]✓[/green] Successfully ingested {count} policy chunks")
        console.print()
        return count
    except Exception as e:
        console.print(f"[red]✗[/red] Policy ingestion failed: {e}")
        console.print()
        return 0


def load_synthetic_data() -> list[dict]:
    """Step 2: Load synthetic transaction data."""
    console.print("[bold cyan]Step 2:[/bold cyan] Loading synthetic test data")
    console.print()

    data_file = Path(__file__).parent.parent / "data" / "synthetic_data.json"

    if not data_file.exists():
        console.print(f"[red]✗[/red] Synthetic data file not found: {data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    console.print(f"[green]✓[/green] Loaded {len(data)} test transactions")
    console.print()

    return data


async def analyze_single_transaction(
    transaction_data: dict,
    expected_outcome: str,
) -> tuple[dict, OrchestratorState]:
    """Analyze a single transaction and return results + full state."""
    transaction = Transaction(**transaction_data["transaction"])
    customer_behavior = CustomerBehavior(**transaction_data["customer_behavior"])

    async with async_session_maker() as db:
        initial_state: OrchestratorState = {
            "transaction": transaction,
            "customer_behavior": customer_behavior,
            "status": "pending",
            "trace": [],
        }
        config: RunnableConfig = {"configurable": {"db_session": db}}

        start_time = time.perf_counter()

        try:
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state, config=config),
                timeout=60.0,
            )

            duration = time.perf_counter() - start_time
            decision = final_state.get("decision")

            if not decision:
                raise ValueError("Pipeline did not produce a decision")

            return {
                "transaction_id": transaction.transaction_id,
                "expected": expected_outcome,
                "actual": decision.decision,
                "confidence": decision.confidence,
                "duration": duration,
                "matches": decision.decision == expected_outcome,
            }, final_state

        except asyncio.TimeoutError:
            duration = time.perf_counter() - start_time
            return {
                "transaction_id": transaction.transaction_id,
                "expected": expected_outcome,
                "actual": "TIMEOUT",
                "confidence": 0.0,
                "duration": duration,
                "matches": False,
            }, None
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "analysis_failed",
                transaction_id=transaction.transaction_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "transaction_id": transaction.transaction_id,
                "expected": expected_outcome,
                "actual": "ERROR",
                "confidence": 0.0,
                "duration": duration,
                "matches": False,
            }, None


async def run_analyses(data: list[dict]) -> tuple[list[dict], list[OrchestratorState]]:
    """Step 3: Run sequential analyses on all transactions."""
    console.print("[bold cyan]Step 3:[/bold cyan] Analyzing transactions (sequential)")
    console.print()

    results = []
    states = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for item in data:
            tx_id = item["transaction"]["transaction_id"]
            task = progress.add_task(f"Analyzing {tx_id}...", total=None)

            result, state = await analyze_single_transaction(
                item,
                item["expected_outcome"],
            )
            results.append(result)
            states.append(state)

            # Real-time result display
            decision = result["actual"]
            confidence = result["confidence"]
            duration = result["duration"]
            match_icon = "✓" if result["matches"] else "✗"
            match_color = "green" if result["matches"] else "red"

            decision_colors = {
                "APPROVE": "green",
                "CHALLENGE": "yellow",
                "BLOCK": "red",
                "ESCALATE_TO_HUMAN": "magenta",
            }
            decision_color = decision_colors.get(decision, "white")

            console.print(
                f"  [{match_color}]{match_icon}[/{match_color}] {tx_id}: "
                f"[{decision_color}]{decision}[/{decision_color}] "
                f"({confidence:.0%}) — {duration:.1f}s"
            )

            progress.update(task, completed=True)

    console.print()
    return results, states


def display_results_table(results: list[dict]):
    """Display summary table of all results."""
    console.print("[bold cyan]Step 4:[/bold cyan] Results Summary")
    console.print()

    table = Table(
        title="Fraud Detection Analysis Results",
        show_header=True,
        header_style="bold magenta",
        title_style="bold cyan",
    )

    table.add_column("ID", style="cyan", width=8)
    table.add_column("Expected", style="yellow", width=18)
    table.add_column("Actual", style="green", width=18)
    table.add_column("✓", justify="center", width=3)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Time", justify="right", width=8)

    matches = 0
    total = len(results)

    for result in results:
        match_icon = "✓" if result["matches"] else "✗"
        match_color = "green" if result["matches"] else "red"

        decision_colors = {
            "APPROVE": "green",
            "CHALLENGE": "yellow",
            "BLOCK": "red",
            "ESCALATE_TO_HUMAN": "magenta",
        }

        actual_color = decision_colors.get(result["actual"], "white")

        if result["matches"]:
            matches += 1

        table.add_row(
            result["transaction_id"],
            result["expected"],
            f"[{actual_color}]{result['actual']}[/{actual_color}]",
            f"[{match_color}]{match_icon}[/{match_color}]",
            f"{result['confidence']:.0%}",
            f"{result['duration']:.1f}s",
        )

    console.print(table)
    console.print()

    # Summary statistics
    accuracy = (matches / total * 100) if total > 0 else 0
    avg_time = sum(r["duration"] for r in results) / total if total > 0 else 0
    avg_confidence = sum(r["confidence"] for r in results) / total if total > 0 else 0

    console.print(f"[bold]Summary Statistics:[/bold]")
    console.print(f"  Total Transactions: {total}")
    console.print(f"  Correct Predictions: [{('green' if accuracy >= 80 else 'yellow')}]{matches}/{total}[/]")
    console.print(f"  Accuracy: [{('green' if accuracy >= 80 else 'yellow' if accuracy >= 60 else 'red')}]{accuracy:.1f}%[/]")
    console.print(f"  Average Confidence: {avg_confidence:.1%}")
    console.print(f"  Average Processing Time: {avg_time:.2f}s")
    console.print()


def display_debate_example(states: list[OrchestratorState]):
    """Step 5: Display a complete debate example."""
    console.print("[bold cyan]Step 5:[/bold cyan] Adversarial Debate Example")
    console.print()

    # Find the first state with a valid debate (preferably CHALLENGE or ESCALATE)
    debate_state = None
    for state in states:
        if state and state.get("debate"):
            decision = state.get("decision")
            if decision and decision.decision in ["CHALLENGE", "ESCALATE_TO_HUMAN"]:
                debate_state = state
                break

    # Fallback: any state with debate
    if not debate_state:
        for state in states:
            if state and state.get("debate"):
                debate_state = state
                break

    if not debate_state:
        console.print("[yellow]⚠[/yellow]  No debate data available in analyzed transactions")
        console.print()
        return

    transaction = debate_state["transaction"]
    debate = debate_state["debate"]
    decision = debate_state["decision"]

    # Transaction header
    console.print(f"[bold]Transaction:[/bold] {transaction.transaction_id}")
    console.print(f"  Amount: {transaction.amount:.2f} {transaction.currency}")
    console.print(f"  Country: {transaction.country} | Channel: {transaction.channel}")
    console.print(f"  Timestamp: {transaction.timestamp}")
    console.print()

    # Pro-Fraud Argument
    pro_fraud_panel = Panel(
        f"[bold]Argument:[/bold]\n{debate.pro_fraud_argument}\n\n"
        f"[bold]Confidence:[/bold] {debate.pro_fraud_confidence:.1%}\n\n"
        f"[bold]Evidence:[/bold]\n" + "\n".join(f"  • {ev}" for ev in debate.pro_fraud_evidence),
        title="[red bold]⚠ Pro-Fraud Agent[/red bold]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(pro_fraud_panel)
    console.print()

    # Pro-Customer Argument
    pro_customer_panel = Panel(
        f"[bold]Argument:[/bold]\n{debate.pro_customer_argument}\n\n"
        f"[bold]Confidence:[/bold] {debate.pro_customer_confidence:.1%}\n\n"
        f"[bold]Evidence:[/bold]\n" + "\n".join(f"  • {ev}" for ev in debate.pro_customer_evidence),
        title="[green bold]✓ Pro-Customer Agent[/green bold]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(pro_customer_panel)
    console.print()

    # Final Decision
    decision_colors = {
        "APPROVE": "green",
        "CHALLENGE": "yellow",
        "BLOCK": "red",
        "ESCALATE_TO_HUMAN": "magenta",
    }
    decision_color = decision_colors.get(decision.decision, "white")

    decision_panel = Panel(
        f"[bold]Decision:[/bold] [{decision_color}]{decision.decision}[/{decision_color}]\n"
        f"[bold]Confidence:[/bold] {decision.confidence:.1%}\n\n"
        f"[bold]Customer Explanation:[/bold]\n{decision.explanation_customer}",
        title="[cyan bold]⚖ Arbiter Decision[/cyan bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(decision_panel)
    console.print()


async def main():
    """Main demo execution."""
    print_header()

    try:
        # Step 1: Ingest policies
        ingest_policies_step()

        # Step 2: Load test data
        data = load_synthetic_data()

        # Step 3: Run analyses
        results, states = await run_analyses(data)

        # Step 4: Display results table
        display_results_table(results)

        # Step 5: Show debate example
        display_debate_example(states)

        console.print("[green]✓[/green] Demo completed successfully!")
        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow]  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]✗[/red] Demo failed: {e}")
        logger.error("demo_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
