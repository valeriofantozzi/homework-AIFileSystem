#!/usr/bin/env python3
"""
Diagnostic CLI tool for the AI File System Agent.
Provides easy access to performance metrics, usage statistics, and health checks.
"""

import asyncio
import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

from agent.diagnostics import (
    get_diagnostic_logger,
    get_performance_summary,
    get_usage_statistics,
    export_diagnostics,
    health_check
)


console = Console()


@click.group()
def cli():
    """AI File System Agent Diagnostic Tools"""
    pass


@cli.command()
@click.option('--hours', default=24, help='Hours to look back for performance data')
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json']), help='Output format')
def performance(hours, output_format):
    """Show performance metrics and statistics."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Gathering performance data...", total=None)
        
        try:
            perf_data = get_performance_summary(hours)
            progress.update(task, description="Processing performance data...")
            
            if output_format == 'json':
                console.print_json(json.dumps(perf_data, indent=2))
                return
            
            # Display as rich table
            if "message" in perf_data:
                console.print(f"[yellow]{perf_data['message']}[/yellow]")
                return
            
            # Main metrics table
            metrics_table = Table(title=f"Performance Summary - Last {hours} Hours")
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", style="green")
            
            metrics_table.add_row("Total Operations", str(perf_data['total_operations']))
            metrics_table.add_row("Successful Operations", str(perf_data['successful_operations']))
            metrics_table.add_row("Success Rate", f"{perf_data['success_rate']:.1%}")
            metrics_table.add_row("Average Duration", f"{perf_data['average_duration_seconds']:.3f}s")
            metrics_table.add_row("Average Memory Usage", f"{perf_data['average_memory_mb']:.2f} MB")
            
            console.print(metrics_table)
            
            # Operations by type
            if perf_data['operations_by_type']:
                ops_table = Table(title="Operations by Type")
                ops_table.add_column("Operation", style="cyan")
                ops_table.add_column("Count", style="green")
                
                for op_type, count in sorted(perf_data['operations_by_type'].items()):
                    ops_table.add_row(op_type, str(count))
                
                console.print(ops_table)
            
            # Slowest operations
            if perf_data['slowest_operations']:
                slow_table = Table(title="Slowest Operations")
                slow_table.add_column("Operation", style="cyan")
                slow_table.add_column("Duration", style="red")
                
                for op in perf_data['slowest_operations']:
                    slow_table.add_row(op['operation'], f"{op['duration']:.3f}s")
                
                console.print(slow_table)
            
        except Exception as e:
            console.print(f"[red]Error gathering performance data: {e}[/red]")


@cli.command()
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json']), help='Output format')
def usage(output_format):
    """Show usage statistics."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Gathering usage statistics...", total=None)
        
        try:
            usage_data = get_usage_statistics()
            
            if output_format == 'json':
                console.print_json(json.dumps(usage_data, indent=2))
                return
            
            # Main statistics table
            stats_table = Table(title="Usage Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="green")
            
            stats_table.add_row("Total Conversations", str(usage_data['conversations']))
            stats_table.add_row("Total Queries", str(usage_data['queries']))
            stats_table.add_row("Total Tool Calls", str(usage_data['tool_calls']))
            stats_table.add_row("Total Errors", str(usage_data['errors']))
            stats_table.add_row("Average Response Time", f"{usage_data['avg_response_time']:.3f}s")
            
            console.print(stats_table)
            
            # Top tools
            if usage_data.get('top_tools'):
                tools_table = Table(title="Most Used Tools")
                tools_table.add_column("Tool", style="cyan")
                tools_table.add_column("Usage Count", style="green")
                
                for tool, count in usage_data['top_tools']:
                    tools_table.add_row(tool, str(count))
                
                console.print(tools_table)
            
            # Error breakdown
            if usage_data.get('error_breakdown'):
                errors_table = Table(title="Error Breakdown")
                errors_table.add_column("Error Type", style="cyan")
                errors_table.add_column("Count", style="red")
                
                for error_type, count in usage_data['error_breakdown'].items():
                    errors_table.add_row(error_type, str(count))
                
                console.print(errors_table)
            
        except Exception as e:
            console.print(f"[red]Error gathering usage statistics: {e}[/red]")


@cli.command()
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json']), help='Output format')
def health(output_format):
    """Perform system health check."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Performing health check...", total=None)
        
        try:
            health_data = health_check()
            
            if output_format == 'json':
                console.print_json(json.dumps(health_data, indent=2))
                return
            
            # Overall status
            status_color = {
                "HEALTHY": "green",
                "DEGRADED": "yellow", 
                "UNHEALTHY": "red",
                "UNKNOWN": "cyan"
            }.get(health_data['overall_status'], "white")
            
            console.print(Panel(
                f"[{status_color}]{health_data['overall_status']}[/{status_color}]",
                title="Overall System Status",
                expand=False
            ))
            
            # Component status table
            components_table = Table(title="Component Health")
            components_table.add_column("Component", style="cyan")
            components_table.add_column("Status", style="bold")
            components_table.add_column("Details")
            
            for component, details in health_data['components'].items():
                status = details['status']
                status_color = {
                    "HEALTHY": "green",
                    "DEGRADED": "yellow",
                    "UNHEALTHY": "red", 
                    "UNKNOWN": "cyan"
                }.get(status, "white")
                
                # Format details
                detail_parts = []
                for key, value in details.items():
                    if key != 'status':
                        detail_parts.append(f"{key}: {value}")
                
                components_table.add_row(
                    component.replace('_', ' ').title(),
                    f"[{status_color}]{status}[/{status_color}]",
                    " | ".join(detail_parts)
                )
            
            console.print(components_table)
            
        except Exception as e:
            console.print(f"[red]Error performing health check: {e}[/red]")


@cli.command()
@click.option('--output', help='Output file path (default: logs/diagnostics_TIMESTAMP.json)')
@click.option('--open', 'open_file', is_flag=True, help='Open the generated file after export')
def export(output, open_file):
    """Export comprehensive diagnostics to a file."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Exporting diagnostics...", total=None)
        
        try:
            output_path = Path(output) if output else None
            exported_file = export_diagnostics(output_path)
            
            progress.update(task, description="Diagnostics exported successfully")
            
            console.print(f"[green]✓[/green] Diagnostics exported to: [cyan]{exported_file}[/cyan]")
            
            # Show file size
            file_size = exported_file.stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            console.print(f"File size: {size_str}")
            
            if open_file:
                import subprocess
                import sys
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", str(exported_file)])
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", str(exported_file)])
                elif sys.platform == "win32":
                    subprocess.run(["start", str(exported_file)], shell=True)
            
        except Exception as e:
            console.print(f"[red]Error exporting diagnostics: {e}[/red]")


@cli.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f)')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.argument('log_type', type=click.Choice(['agent', 'performance', 'usage', 'errors', 'all']))
def logs(follow, lines, log_type):
    """View log files."""
    
    log_files = {
        'agent': 'logs/agent_activity.log',
        'performance': 'logs/performance.jsonl',
        'usage': 'logs/usage.jsonl', 
        'errors': 'logs/errors.log'
    }
    
    if log_type == 'all':
        # Show summary of all logs
        console.print("[bold]Log File Summary[/bold]")
        
        for log_name, log_path in log_files.items():
            log_file = Path(log_path)
            if log_file.exists():
                stat = log_file.stat()
                size_mb = stat.st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"[cyan]{log_name}[/cyan]: {size_mb:.2f} MB, modified {modified}")
            else:
                console.print(f"[dim]{log_name}[/dim]: File not found")
        return
    
    log_file = Path(log_files[log_type])
    
    if not log_file.exists():
        console.print(f"[red]Log file not found: {log_file}[/red]")
        return
    
    try:
        if follow:
            console.print(f"[cyan]Following {log_file}[/cyan] (Press Ctrl+C to stop)")
            # Simple tail -f implementation
            import time
            with open(log_file, 'r') as f:
                # Seek to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    console.print(line.rstrip())
        else:
            # Show last N lines
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                console.print(f"[cyan]Last {len(recent_lines)} lines from {log_file}[/cyan]")
                console.print("-" * 80)
                
                for line in recent_lines:
                    console.print(line.rstrip())
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following log[/yellow]")
    except Exception as e:
        console.print(f"[red]Error reading log file: {e}[/red]")


@cli.command()
def monitor():
    """Real-time monitoring dashboard."""
    
    console.print("[bold]AI File System Agent - Real-time Monitor[/bold]")
    console.print("Press Ctrl+C to stop monitoring\n")
    
    try:
        import time
        while True:
            # Clear screen (simple approach)
            console.clear()
            
            console.print(f"[bold]Monitoring Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold]\n")
            
            # Health status
            try:
                health_data = health_check()
                status = health_data['overall_status']
                status_color = {
                    "HEALTHY": "green",
                    "DEGRADED": "yellow",
                    "UNHEALTHY": "red"
                }.get(status, "white")
                
                console.print(f"System Status: [{status_color}]{status}[/{status_color}]")
            except:
                console.print("System Status: [red]ERROR[/red]")
            
            # Recent performance
            try:
                perf_data = get_performance_summary(1)  # Last hour
                if "total_operations" in perf_data:
                    console.print(f"Operations (1h): {perf_data['total_operations']}")
                    console.print(f"Success Rate: {perf_data.get('success_rate', 0):.1%}")
                    console.print(f"Avg Duration: {perf_data.get('average_duration_seconds', 0):.3f}s")
            except:
                console.print("Performance: [red]ERROR[/red]")
            
            # Usage stats
            try:
                usage_data = get_usage_statistics()
                console.print(f"Total Conversations: {usage_data['conversations']}")
                console.print(f"Total Queries: {usage_data['queries']}")
                console.print(f"Total Errors: {usage_data['errors']}")
            except:
                console.print("Usage Stats: [red]ERROR[/red]")
            
            console.print("\n[dim]Refreshing in 5 seconds...[/dim]")
            time.sleep(5)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


if __name__ == '__main__':
    cli()
