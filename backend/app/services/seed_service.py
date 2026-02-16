"""Seed service for loading and testing synthetic fraud data."""

import asyncio
import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..agents.orchestrator import analyze_transaction
from ..db.engine import async_session as async_session_maker
from ..models import CustomerBehavior, FraudDecision, Transaction
from ..utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


async def load_synthetic_data(file_path: str = "data/synthetic_data.json") -> list[dict[str, Any]]:
    """Load synthetic transaction data from JSON file."""
    data_file = Path(__file__).parent.parent.parent / file_path

    if not data_file.exists():
        raise FileNotFoundError(f"Synthetic data file not found: {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    console.print(f"[green]✓[/green] Loaded {len(data)} transactions from {data_file.name}")
    return data


async def run_single_analysis(
    transaction_data: dict[str, Any],
    expected_outcome: str,
) -> dict[str, Any]:
    """Run fraud analysis on a single transaction."""
    transaction = Transaction(**transaction_data["transaction"])
    customer_behavior = CustomerBehavior(**transaction_data["customer_behavior"])

    async with async_session_maker() as db:
        try:
            decision: FraudDecision = await analyze_transaction(
                transaction,
                customer_behavior,
                db,
            )

            matches = decision.decision == expected_outcome

            return {
                "transaction_id": transaction.transaction_id,
                "expected": expected_outcome,
                "actual": decision.decision,
                "confidence": decision.confidence,
                "matches": matches,
                "reason": transaction_data.get("reason", "N/A"),
                "explanation": decision.explanation_customer[:100] + "..."
                if len(decision.explanation_customer) > 100
                else decision.explanation_customer,
            }
        except Exception as e:
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
                "matches": False,
                "reason": str(e),
                "explanation": f"Error: {str(e)}",
            }


async def run_batch_analysis(parallel: bool = False) -> list[dict[str, Any]]:
    """Run fraud analysis on all synthetic data.

    Args:
        parallel: If True, run analyses in parallel. If False, run sequentially.

    Returns:
        List of analysis results.
    """
    data = await load_synthetic_data()

    console.print(f"\n[bold cyan]Running {len(data)} transaction analyses[/bold cyan]")
    console.print(f"Mode: {'Parallel' if parallel else 'Sequential'}\n")

    results = []

    if parallel:
        # Run all analyses in parallel
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing transactions...", total=None)

            tasks = [run_single_analysis(item, item["expected_outcome"]) for item in data]
            results = await asyncio.gather(*tasks)

            progress.update(task, completed=True)
    else:
        # Run analyses sequentially with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for item in data:
                task_id = progress.add_task(
                    f"Analyzing {item['transaction']['transaction_id']}...",
                    total=None,
                )

                result = await run_single_analysis(item, item["expected_outcome"])
                results.append(result)

                progress.update(task_id, completed=True)

    return results


def display_results(results: list[dict[str, Any]]) -> None:
    """Display analysis results in a rich table."""
    table = Table(
        title="Fraud Detection Analysis Results", show_header=True, header_style="bold magenta"
    )

    table.add_column("Transaction ID", style="cyan", width=12)
    table.add_column("Expected", style="yellow", width=18)
    table.add_column("Actual", style="green", width=18)
    table.add_column("Match", justify="center", width=7)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Reason", style="dim", width=50)

    matches = 0
    total = len(results)

    for result in results:
        match_icon = "✓" if result["matches"] else "✗"
        match_color = "green" if result["matches"] else "red"

        if result["matches"]:
            matches += 1

        table.add_row(
            result["transaction_id"],
            result["expected"],
            result["actual"],
            f"[{match_color}]{match_icon}[/{match_color}]",
            f"{result['confidence']:.2f}",
            result["reason"],
        )

    console.print(table)

    # Summary
    accuracy = (matches / total) * 100 if total > 0 else 0
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Total: {total}")
    console.print(f"  Matches: [green]{matches}[/green]")
    console.print(f"  Mismatches: [red]{total - matches}[/red]")
    console.print(
        f"  Accuracy: [{'green' if accuracy >= 80 else 'yellow' if accuracy >= 60 else 'red'}]{accuracy:.1f}%[/]\n"
    )


async def seed_and_test(parallel: bool = False) -> None:
    """Load synthetic data and run test analyses.

    Args:
        parallel: If True, run analyses in parallel. If False, run sequentially.
    """
    console.print("[bold blue]═══ Fraud Detection Seed & Test ═══[/bold blue]\n")

    try:
        results = await run_batch_analysis(parallel=parallel)
        display_results(results)

        console.print("[green]✓[/green] Testing completed successfully!\n")
    except Exception as e:
        console.print(f"[red]✗[/red] Error during testing: {str(e)}\n")
        logger.error("seed_test_error", error=str(e), exc_info=True)
        raise


async def main():
    """CLI entry point for seed service."""
    import sys

    parallel = "--parallel" in sys.argv or "-p" in sys.argv
    await seed_and_test(parallel=parallel)


if __name__ == "__main__":
    asyncio.run(main())
