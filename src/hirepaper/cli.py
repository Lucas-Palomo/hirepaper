import os
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

# Kept locally because doctor is explicitly out of scope for the API refactor.
# Do not use in CLI commands; use the API layer instead.
def _latex_env(build_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    xdg_cache_home = build_dir / "xdg-cache"
    texmf_var = build_dir / "texmf-var"
    xdg_cache_home.mkdir(parents=True, exist_ok=True)
    texmf_var.mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    env["TEXMFVAR"] = str(texmf_var)
    env["TEXMFCACHE"] = str(texmf_var)
    return env


from .api import (
    PDFGenerateError,
    bootstrap_candidate_file,
    bootstrap_config_file,
    check_pdf_file,
    generate_pdf_file,
    lint_candidate_file,
    match_candidate_file,
    tailor_candidate_file,
    generate_linkedin_report_file,
)
def _show_group_help(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _show_explicit_help(ctx: typer.Context) -> None:
    typer.echo(ctx.parent.get_help() if ctx.parent is not None else ctx.get_help())
    raise typer.Exit()


app = typer.Typer(
    help="hirepaper — JSON → LaTeX → PDF",
    callback=_show_group_help,
    invoke_without_command=True,
)


content_app = typer.Typer(
    help="Analyze and transform candidate source data",
    callback=_show_group_help,
    invoke_without_command=True,
)
pdf_app = typer.Typer(
    help="Generate and validate PDF artifacts",
    callback=_show_group_help,
    invoke_without_command=True,
)
llm_app = typer.Typer(
    help="LLM infrastructure diagnostics (health, usage)",
    callback=_show_group_help,
    invoke_without_command=True,
)
linkedin_app = typer.Typer(
    help="Generate LinkedIn-focused profile reports from canonical candidate data",
    callback=_show_group_help,
    invoke_without_command=True,
)
app.add_typer(content_app, name="content")
app.add_typer(pdf_app, name="pdf")
app.add_typer(llm_app, name="llm")
app.add_typer(linkedin_app, name="linkedin")


@app.command("help", help="Show this help message and exit.")
def app_help(ctx: typer.Context) -> None:
    _show_explicit_help(ctx)


@content_app.command("help", help="Show this help message and exit.")
def content_help(ctx: typer.Context) -> None:
    _show_explicit_help(ctx)


@pdf_app.command("help", help="Show this help message and exit.")
def pdf_help(ctx: typer.Context) -> None:
    _show_explicit_help(ctx)


@llm_app.command("help", help="Show this help message and exit.")
def llm_help(ctx: typer.Context) -> None:
    _show_explicit_help(ctx)


@linkedin_app.command("help", help="Show this help message and exit.")
def linkedin_help(ctx: typer.Context) -> None:
    _show_explicit_help(ctx)


# ---------------------------------------------------------------------------
# Shared command implementations (thin adapters over the API layer)
# ---------------------------------------------------------------------------

def _cmd_generate(
    input: Path, output: str, locale: str, density: str, layout: str, log: str | None,
) -> None:
    try:
        result = generate_pdf_file(
            input, output,
            locale=locale, density=density, layout=layout,
            log=log,
        )
    except PDFGenerateError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    if result.build_status == "success" and result.artifact_validation_status == "passed":
        typer.echo(f"Generated: {result.output_path}")
        if log:
            typer.echo("", err=True)
            typer.echo(f"Log archive saved: {log}", err=True)
            typer.echo(
                "WARNING: Log archive may contain candidate data, rendered LaTeX, and compiler diagnostics.",
                err=True,
            )
    elif result.build_status == "success" and result.artifact_validation_status == "failed":
        typer.echo("PDF generation produced an invalid artifact", err=True)
        typer.echo(f"  - {result.validation_message}", err=True)
        if log:
            typer.echo(f"Log archive saved: {log}", err=True)
            typer.echo("Check the archive for luaotfload, fontspec, or artifact validation details", err=True)
        raise typer.Exit(code=1)
    else:
        typer.echo("PDF compilation failed (engine: lualatex)", err=True)
        if log:
            typer.echo(f"Log archive saved: {log}", err=True)
            typer.echo("Check the archive for LuaLaTeX stdout/stderr and intermediate build artifacts", err=True)
        raise typer.Exit(code=1)


def _cmd_pdf_check(pdf: Path) -> None:
    try:
        exit_code = check_pdf_file(pdf)
    except PDFGenerateError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    sys.exit(exit_code)


def _cmd_content_lint(input: Path) -> None:
    try:
        result = lint_candidate_file(input)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except (ValueError, KeyError) as e:
        typer.echo(f"Error: invalid input data — {e}", err=True)
        raise typer.Exit(code=1)

    for msg in result.messages:
        typer.echo(msg)

    if result.fail > 0:
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

@app.command(
    help="Run environment diagnostics and dependency checks for the local hirepaper setup."
)
def doctor():
    """Check local runtime readiness and required host tooling."""
    ok = True

    typer.echo("== hirepaper doctor ==")

    py_version = sys.version_info
    if py_version.major >= 3 and py_version.minor >= 10:
        typer.echo(f"[OK] Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        typer.echo(f"[FAIL] Python >=3.10 required, found {py_version.major}.{py_version.minor}")
        ok = False

    latex_ok = False
    r = subprocess.run(["lualatex", "--version"], capture_output=True, text=True)
    if r.returncode == 0:
        version_line = r.stdout.splitlines()[0] if r.stdout else "unknown"
        typer.echo(f"[OK] lualatex: {version_line}")
        latex_ok = True

        kpse = subprocess.run(["kpsewhich", "luaotfload.lua"], capture_output=True, text=True)
        if kpse.returncode == 0:
            typer.echo("[OK] luaotfload: found")
        else:
            typer.echo("[FAIL] luaotfload: not found (install texlive-luatex)", err=True)
            ok = False
    else:
        typer.echo("[WARN] lualatex: not found")

    if not latex_ok:
        typer.echo("[FAIL] lualatex not found (install texlive or equivalent)", err=True)
        ok = False

    r = subprocess.run(["which", "rsvg-convert"], capture_output=True, text=True)
    if r.returncode == 0:
        typer.echo("[OK] rsvg-convert: available (for icon conversion)")
    else:
        typer.echo("[FAIL] rsvg-convert: not found (install librsvg)", err=True)
        ok = False

    for prog in ("pdftotext", "pdffonts"):
        r = subprocess.run(["which", prog], capture_output=True, text=True)
        if r.returncode == 0:
            typer.echo(f"[OK] {prog} is available")
        else:
            typer.echo(f"[FAIL] {prog}: not found (install poppler-utils)", err=True)
            ok = False

    r = subprocess.run(["which", "exiftool"], capture_output=True, text=True)
    if r.returncode == 0:
        typer.echo("[OK] exiftool is available")
    else:
        typer.echo("[FAIL] exiftool: not found (install perl-image-exiftool)", err=True)
        ok = False

    typer.echo("")
    typer.echo("-- LuaLaTeX + fontspec + DejaVu Sans compilation test --")
    with tempfile.TemporaryDirectory(prefix="hirepaper-doctor-") as tmp:
        build = Path(tmp)
        latex_env = _latex_env(build)
        test_tex = build / "doctor-test.tex"
        test_tex.write_text(
            "\\documentclass{article}\n"
            "\\usepackage{fontspec}\n"
            "\\setmainfont{DejaVu Sans}\n"
            "\\begin{document}\n"
            "Hello world --- hirepaper doctor check.\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        r = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", test_tex.name],
            cwd=build,
            capture_output=True,
            text=True,
            env=latex_env,
        )
        test_pdf = build / "doctor-test.pdf"
        if test_pdf.exists() and test_pdf.stat().st_size > 0:
            typer.echo("[OK] Minimal LuaLaTeX compilation succeeded")
            r2 = subprocess.run(["pdftotext", str(test_pdf), "-"], capture_output=True, text=True)
            if r2.returncode == 0 and "Hello world" in r2.stdout:
                typer.echo("[OK] Text extraction from minimal PDF works")
            else:
                typer.echo("[FAIL] Text extraction from minimal PDF failed", err=True)
                ok = False
            r3 = subprocess.run(["pdffonts", str(test_pdf)], capture_output=True, text=True)
            lines = r3.stdout.splitlines()
            if r3.returncode == 0 and len(lines) >= 3:
                typer.echo("[OK] Fonts embedded in minimal PDF")
                has_unicode = any("Identity-H" in line for line in lines[2:])
                if has_unicode:
                    typer.echo("[OK] Fonts expose Unicode mapping")
                else:
                    typer.echo("[WARN] Fonts may not expose Unicode mapping")
            else:
                typer.echo("[FAIL] No fonts found in minimal PDF (DejaVu Sans may not be installed)", err=True)
                ok = False
        else:
            typer.echo("[FAIL] Minimal LuaLaTeX compilation failed", err=True)
            if not test_pdf.exists():
                typer.echo("  PDF not produced -- check lualatex, fontspec, or writable font cache", err=True)
            ok = False

    if ok:
        typer.echo("")
        typer.echo("All checks passed.")
    else:
        typer.echo("")
        typer.echo("Some checks failed.", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# pdf subcommand group
# ---------------------------------------------------------------------------

@pdf_app.command("generate", help="Generate a PDF resume from a candidate JSON file.")
def pdf_generate(
    ctx: typer.Context,
    input: Path = typer.Argument(
        None,
        help="Path to the candidate JSON file",
    ),
    output: str = typer.Option(
        None,
        "--output", "-o",
        help="Path for the generated PDF file",
    ),
    locale: str = typer.Option(
        "en",
        "--locale", "-l",
        help="Output locale (en, pt-BR)",
    ),
    density: str = typer.Option(
        "compact",
        "--density",
        help="Rendering density (compact, full)",
    ),
    layout: str = typer.Option(
        "standard",
        "--layout",
        help="Visual layout selector. Current supported value: standard. Reserved for future layouts.",
    ),
    log: str | None = typer.Option(
        None,
        "--log",
        help="Save build logs as a ZIP archive to this path. "
        "WARNING: Logs may contain candidate data, rendered LaTeX, intermediate artifacts, "
        "and compiler diagnostics.",
    ),
):
    if input is None or output is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _cmd_generate(input, output, locale, density, layout, log)


@pdf_app.command("check", help="Validate a PDF for ATS safety and quality.")
def pdf_check(
    ctx: typer.Context,
    pdf: Path = typer.Argument(
        None,
        help="Path to the PDF file to validate",
    ),
):
    if pdf is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _cmd_pdf_check(pdf)


# ---------------------------------------------------------------------------
# content subcommand group
# ---------------------------------------------------------------------------

@content_app.command("lint", help="Validate candidate JSON structure and quality.")
def content_lint(
    ctx: typer.Context,
    input: Path = typer.Argument(
        None,
        help="Path to the candidate JSON file",
    ),
):
    if input is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _cmd_content_lint(input)


@content_app.command("init", help="Bootstrap a starter candidate JSON from the bundled example.")
def content_init(
    output: str = typer.Option(
        "candidate.json",
        "--output",
        help="Output path for the starter candidate JSON (default: ./candidate.json)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite the destination file if it already exists",
    ),
):
    try:
        path = bootstrap_candidate_file(output, force=force)
    except (FileNotFoundError, FileExistsError, OSError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Created: {path}")
    typer.echo("This is a starter example candidate. Edit it and validate with `hirepaper content lint`.")


def _run_content_hello(command_name: str, config_path: str | None, verbose: int = 0) -> None:
    from .llm.client import LLMClientError, send_hello
    from .llm.config import LLMConfigError, load_config

    try:
        cfg = load_config(config_path, profile="content_tailor")
    except LLMConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"LLM connectivity test: {command_name}")
    typer.echo(f"Model: {cfg.model}")
    typer.echo(f"Endpoint: {cfg.base_url}")
    typer.echo("")

    try:
        text = send_hello(cfg, verbose=verbose)
    except LLMClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("Response:")
    typer.echo(text)


@content_app.command("match", help="Compare a candidate JSON against a vacancy with LLM analysis.")
def content_match(
    ctx: typer.Context,
    candidate: Path = typer.Argument(
        None,
        help="Path to the candidate JSON file",
    ),
    vacancy: Path = typer.Argument(
        None,
        help="Path to the raw vacancy description text file",
    ),
    config: str = typer.Option(
        None,
        "--config",
        help="Optional TOML config override. If omitted, the CLI loads `./config.toml` when present; "
        "otherwise it resolves configuration from environment variables. "
        "Use the TOML section `llm.content_match` for match-specific timeout/token settings.",
    ),
    locale: str = typer.Option(
        "en",
        "--locale", "-l",
        help="Response locale for the analysis (e.g. en, pt-BR)",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text (default), md, or json",
    ),
    output: str = typer.Option(
        None,
        "--output",
        help="Save the final rendered result to this path",
    ),
    log: str = typer.Option(
        None,
        "--log",
        help="Save execution logs as a ZIP archive to this path. "
        "WARNING: Logs may contain full candidate payload, vacancy text, "
        "prompt, model output, and usage metadata — handle as sensitive data.",
    ),
    prompt: str = typer.Option(
        None,
        "--prompt",
        help="Optional plain-text prompt file. Fully replaces the built-in default matching prompt.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Restrict analysis to explicit evidence only; requires --inference=low",
    ),
    inference: str = typer.Option(
        "medium",
        "--inference",
        help="Inference level: low (conservative), medium (balanced), high (broader semantic)",
    ),
    timeout_seconds: int = typer.Option(
        None,
        "--timeout-seconds",
        help="Override request timeout in seconds for this run. "
        "Defaults to the resolved content match config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    max_tokens: int = typer.Option(
        None,
        "--max-tokens",
        help="Override response token limit for this run. "
        "Defaults to the resolved content match config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose", "-v",
        count=True,
        help="Increase verbosity (-v curl+response, -vv LiteLLM debug, -vvv full HTTP trace)",
    ),
):
    _cmd_content_match(
        candidate,
        vacancy,
        config,
        locale,
        format,
        output,
        log,
        prompt,
        strict,
        inference,
        timeout_seconds,
        max_tokens,
        verbose,
    )


def _cmd_content_match(
    candidate: Path,
    vacancy: Path,
    config_path: str | None,
    locale: str,
    format: str,
    output: str | None,
    log: str | None,
    prompt: str | None,
    strict: bool,
    inference: str,
    timeout_seconds: int | None,
    max_tokens: int | None,
    verbose: int,
) -> None:
    from .content_match import ContentMatchError

    if format not in ("text", "md", "json"):
        typer.echo(f"Error: unsupported --format '{format}' (supported: text, md, json)", err=True)
        raise typer.Exit(code=1)

    try:
        report, validated, meta = match_candidate_file(
            candidate_path=candidate,
            vacancy_path=vacancy,
            config_path=config_path,
            locale=locale,
            format=format,
            output=output,
            log=log,
            prompt=prompt,
            strict=strict,
            inference=inference,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            verbose=verbose,
        )
    except ContentMatchError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(report)

    if log:
        typer.echo("", err=True)
        typer.echo(f"Log archive saved: {log}", err=True)
        typer.echo("WARNING: Log archive may contain sensitive candidate, vacancy, and model data.", err=True)


@content_app.command("tailor", help="Tailor a candidate JSON to a vacancy using LLM planning.")
def content_tailor(
    ctx: typer.Context,
    candidate: Path = typer.Argument(
        None,
        help="Path to the candidate JSON file",
    ),
    vacancy: Path = typer.Argument(
        None,
        help="Path to the raw vacancy description text file",
    ),
    output: str = typer.Option(
        None,
        "--output",
        help="Required. Path for the final tailored candidate JSON (primary artifact).",
    ),
    config: str = typer.Option(
        None,
        "--config",
        help="Optional TOML config override. If omitted, the CLI loads `./config.toml` when present; "
        "otherwise it resolves configuration from environment variables. "
        "Use the TOML section `llm.content_tailor` for tailor-specific timeout/token settings.",
    ),
    locale: str = typer.Option(
        "en",
        "--locale", "-l",
        help="Response/report locale (e.g. en, pt-BR)",
    ),
    mode: str = typer.Option(
        "conservative",
        "--mode",
        help="Tailoring mode: conservative (default) or rewrite",
    ),
    inference: str = typer.Option(
        "medium",
        "--inference",
        help="Inference level: low, medium (default), high",
    ),
    extra_context: list[str] = typer.Option(
        None,
        "--extra-context",
        help="Additional UTF-8 text source to support tailoring (repeatable)",
    ),
    report_output: str = typer.Option(
        None,
        "--report-output",
        help="Optional. Save tailoring report separately to this path.",
    ),
    report_format: str = typer.Option(
        "text",
        "--report-format",
        help="Report format: text (default), md, or json",
    ),
    log: str = typer.Option(
        None,
        "--log",
        help="Save execution logs as a ZIP archive to this path. "
        "WARNING: Logs may contain full candidate payload, vacancy text, "
        "prompts, model output, and usage metadata — handle as sensitive data.",
    ),
    prompt: str = typer.Option(
        None,
        "--prompt",
        help="Optional plain-text prompt file for the plan stage. Fully replaces the built-in default.",
    ),
    timeout_seconds: int = typer.Option(
        None,
        "--timeout-seconds",
        help="Override request timeout in seconds for this run. "
        "Defaults to the resolved content tailor config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    max_tokens: int = typer.Option(
        None,
        "--max-tokens",
        help="Override response token limit for this run. "
        "Defaults to the resolved content tailor config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow overwrite of existing output/report/log destinations.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress the detailed human-readable terminal report.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose", "-v",
        count=True,
        help="Increase verbosity (-v curl+response, -vv LiteLLM debug, -vvv full HTTP trace)",
    ),
):
    if candidate is None or vacancy is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _cmd_content_tailor(
        candidate,
        vacancy,
        output,
        config,
        locale,
        mode,
        inference,
        extra_context,
        report_output,
        report_format,
        log,
        prompt,
        timeout_seconds,
        max_tokens,
        force,
        quiet,
        verbose,
    )


def _cmd_content_tailor(
    candidate: Path,
    vacancy: Path,
    output: str | None,
    config_path: str | None,
    locale: str,
    mode: str,
    inference: str,
    extra_context: list[str] | None,
    report_output: str | None,
    report_format: str,
    log: str | None,
    prompt: str | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
    force: bool,
    quiet: bool,
    verbose: int,
) -> None:
    from .content_tailor import ContentTailorError

    if report_format not in ("text", "md", "json"):
        typer.echo(f"Error: unsupported --report-format '{report_format}' (supported: text, md, json)", err=True)
        raise typer.Exit(code=1)

    if mode not in ("conservative", "rewrite"):
        typer.echo(f"Error: unsupported --mode '{mode}' (supported: conservative, rewrite)", err=True)
        raise typer.Exit(code=1)

    if inference not in ("low", "medium", "high"):
        typer.echo(f"Error: unsupported --inference '{inference}' (supported: low, medium, high)", err=True)
        raise typer.Exit(code=1)

    if output is None:
        typer.echo("Error: --output is required", err=True)
        raise typer.Exit(code=1)

    destinations = [Path(output)]
    if report_output:
        destinations.append(Path(report_output))
    if log:
        destinations.append(Path(log))

    for dst in destinations:
        if dst.exists():
            if force:
                continue
            if sys.stdin.isatty():
                try:
                    response = input(f"File already exists: {dst}. Overwrite? [y/N] ")
                    if response.strip().lower() != "y":
                        typer.echo("Aborted by user.", err=True)
                        raise typer.Exit(code=1)
                except (EOFError, KeyboardInterrupt):
                    typer.echo("", err=True)
                    typer.echo("Aborted.", err=True)
                    raise typer.Exit(code=1)
            else:
                typer.echo(
                    f"Error: destination already exists: {dst}. "
                    f"Use --force to overwrite or choose another path.",
                    err=True,
                )
                raise typer.Exit(code=1)

    try:
        report_str, report_data, meta = tailor_candidate_file(
            candidate_path=candidate,
            vacancy_path=vacancy,
            output=output,
            config_path=config_path,
            locale=locale,
            mode=mode,
            inference=inference,
            extra_context=extra_context,
            report_output=report_output,
            report_format=report_format,
            log=log,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            verbose=verbose,
        )
    except ContentTailorError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    if not quiet:
        typer.echo(report_str)
    else:
        typer.echo(f"Tailored candidate saved: {output}")

    if report_output and not quiet:
        typer.echo("", err=True)
        typer.echo(f"Report saved: {report_output}", err=True)

    typer.echo("", err=True)
    typer.echo(f"Tailored candidate: {output}", err=True)

    if log:
        typer.echo(f"Log archive saved: {log}", err=True)
        typer.echo("WARNING: Log archive may contain sensitive candidate, vacancy, and model data.", err=True)

    lint_status = (meta or {}).get("lint_status_after", "unknown")
    if lint_status == "warning":
        typer.echo("Tailored candidate passed lint with warnings — review before use.", err=True)


# ---------------------------------------------------------------------------
# linkedin subcommand group
# ---------------------------------------------------------------------------

def _cmd_linkedin_generate(
    candidate: Path,
    output: str | None,
    config_path: str | None,
    locale: str,
    format: str,
    log: str | None,
    prompt: str | None,
    extra_context: list[str] | None,
    timeout_seconds: int | None,
    max_tokens: int | None,
    force: bool,
    quiet: bool,
    verbose: int,
) -> None:
    from .linkedin_generate import LinkedInGenerateError

    if format not in ("txt", "md", "json"):
        typer.echo(f"Error: unsupported --format '{format}' (supported: txt, md, json)", err=True)
        raise typer.Exit(code=1)

    if output is None:
        typer.echo("Error: --output is required", err=True)
        raise typer.Exit(code=1)

    destinations = [Path(output)]
    if log:
        destinations.append(Path(log))

    for dst in destinations:
        if dst.exists():
            if force:
                continue
            if sys.stdin.isatty():
                try:
                    response = input(f"File already exists: {dst}. Overwrite? [y/N] ")
                    if response.strip().lower() != "y":
                        typer.echo("Aborted by user.", err=True)
                        raise typer.Exit(code=1)
                except (EOFError, KeyboardInterrupt):
                    typer.echo("", err=True)
                    typer.echo("Aborted.", err=True)
                    raise typer.Exit(code=1)
            else:
                typer.echo(
                    f"Error: destination already exists: {dst}. "
                    f"Use --force to overwrite or choose another path.",
                    err=True,
                )
                raise typer.Exit(code=1)

    try:
        report_str, report_data, meta = generate_linkedin_report_file(
            candidate_path=candidate,
            output=output,
            config_path=config_path,
            locale=locale,
            format=format,
            log=log,
            prompt=prompt,
            extra_context=extra_context,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            verbose=verbose,
        )
    except LinkedInGenerateError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    if not quiet:
        typer.echo(report_str)
    else:
        typer.echo(f"LinkedIn report saved: {output}", err=True)

    typer.echo("", err=True)
    typer.echo(f"LinkedIn report saved: {output}", err=True)

    if log:
        typer.echo(f"Log archive saved: {log}", err=True)
        typer.echo("WARNING: Log archive may contain sensitive candidate and model data.", err=True)


@linkedin_app.command("generate", help="Generate a LinkedIn-focused profile report from a candidate JSON file.")
def linkedin_generate(
    ctx: typer.Context,
    candidate: Path = typer.Argument(
        None,
        help="Path to the canonical candidate JSON file",
    ),
    output: str = typer.Option(
        None,
        "--output", "-o",
        help="Required. Path for the final LinkedIn report artifact.",
    ),
    config: str = typer.Option(
        None,
        "--config",
        help="Optional TOML config override. If omitted, the CLI loads `./config.toml` when present; "
        "otherwise it resolves configuration from environment variables. "
        "Use the TOML section `llm.linkedin_generate` for LinkedIn-specific timeout/token settings.",
    ),
    locale: str = typer.Option(
        "en",
        "--locale", "-l",
        help="Report locale (e.g. en, pt-BR)",
    ),
    format: str = typer.Option(
        None,
        "--format",
        help="Required. Output format: txt (human-readable), md, or json (structured).",
    ),
    log: str = typer.Option(
        None,
        "--log",
        help="Save execution logs as a ZIP archive to this path. "
        "WARNING: Logs may contain full candidate payload, prompt, "
        "model output, and usage metadata — handle as sensitive data.",
    ),
    prompt: str = typer.Option(
        None,
        "--prompt",
        help="Optional plain-text prompt file. Fully replaces the built-in default LinkedIn prompt.",
    ),
    extra_context: list[str] = typer.Option(
        None,
        "--extra-context",
        help="Additional UTF-8 text source to support LinkedIn guidance (repeatable)",
    ),
    timeout_seconds: int = typer.Option(
        None,
        "--timeout-seconds",
        help="Override request timeout in seconds for this run. "
        "Defaults to the resolved LinkedIn generate config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    max_tokens: int = typer.Option(
        None,
        "--max-tokens",
        help="Override response token limit for this run. "
        "Defaults to the resolved LinkedIn generate config value "
        "(profile-specific, then defaults, then command fallback).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow overwrite of existing output/log destinations.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress the detailed human-readable terminal report.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose", "-v",
        count=True,
        help="Increase verbosity (-v curl+response, -vv LiteLLM debug, -vvv full HTTP trace)",
    ),
):
    if candidate is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _cmd_linkedin_generate(
        candidate,
        output,
        config,
        locale,
        format,
        log,
        prompt,
        extra_context,
        timeout_seconds,
        max_tokens,
        force,
        quiet,
        verbose,
    )


# ---------------------------------------------------------------------------
# llm subcommand group
# ---------------------------------------------------------------------------

def _run_llm_health(config_path: str | None, verbose: int = 0) -> None:
    from .llm.client import LLMClientError, check_health
    from .llm.config import LLMConfigError, load_config

    try:
        cfg = load_config(config_path)
    except LLMConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("LLM health check")
    typer.echo(f"Model: {cfg.model}")
    typer.echo(f"Endpoint: {cfg.base_url}")
    typer.echo("")
    typer.echo("Method: minimal completion request (no dedicated proxy health endpoint)")
    typer.echo("")

    try:
        check_health(cfg, verbose=verbose)
    except LLMClientError as e:
        typer.echo(f"[FAIL] Completion request failed — inferred health: UNHEALTHY", err=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("[OK] Completion request succeeded — inferred health: HEALTHY")


def _print_usage(data: dict, prefix: str = "") -> None:
    for key, value in data.items():
        label = key.replace("_", " ").title()
        if isinstance(value, dict):
            typer.echo(f"{prefix}{label}:")
            _print_usage(value, prefix + "  ")
        else:
            typer.echo(f"{prefix}{label}: {value}")


def _run_llm_usage(config_path: str | None, verbose: int = 0) -> None:
    from .llm.client import LLMClientError, get_usage
    from .llm.config import LLMConfigError, load_config

    try:
        cfg = load_config(config_path)
    except LLMConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("LLM usage diagnostic")
    typer.echo(f"Model: {cfg.model}")
    typer.echo(f"Endpoint: {cfg.base_url}")
    typer.echo("")

    try:
        tokens = get_usage(cfg, verbose=verbose)
    except LLMClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    _print_usage(tokens)


@llm_app.command("health", help="Check LLM connectivity with a minimal completion request.")
def llm_health(
    ctx: typer.Context,
    config: str = typer.Option(
        None,
        "--config",
        help="Optional TOML config override. If omitted, the CLI loads `./config.toml` when present; "
        "otherwise it resolves configuration from environment variables.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose", "-v",
        count=True,
        help="Increase verbosity (-v curl+response, -vv LiteLLM debug, -vvv full HTTP trace)",
    ),
):
    _run_llm_health(config, verbose=verbose)


@llm_app.command("usage", help="Show per-request token usage diagnostics.")
def llm_usage(
    ctx: typer.Context,
    config: str = typer.Option(
        None,
        "--config",
        help="Optional TOML config override. If omitted, the CLI loads `./config.toml` when present; "
        "otherwise it resolves configuration from environment variables.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose", "-v",
        count=True,
        help="Increase verbosity (-v curl+response, -vv LiteLLM debug, -vvv full HTTP trace)",
    ),
):
    _run_llm_usage(config, verbose=verbose)


@app.command(
    help="Bootstrap a local config.toml from the bundled template."
)
def init(
    output: str = typer.Option(
        "config.toml",
        "--output",
        help="Output path for the generated config file (default: ./config.toml)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite the destination file if it already exists",
    ),
):
    try:
        path = bootstrap_config_file(output, force=force)
    except (FileNotFoundError, FileExistsError, OSError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Created: {path}")
    typer.echo("This file is an optional TOML override; environment variables are still supported.")


if __name__ == "__main__":
    app()
