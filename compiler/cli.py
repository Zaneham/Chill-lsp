"""
CHILL Compiler CLI
Command-line interface for the CHILL to C compiler
"""

import sys
import argparse
from pathlib import Path

# Support both relative and absolute imports
try:
    from .parser import parse, ParseError
    from .semantic import analyze
    from .codegen import generate
except ImportError:
    from parser import parse, ParseError
    from semantic import analyze
    from codegen import generate


def compile_file(input_path: str, output_path: str = None,
                 check_only: bool = False, verbose: bool = False) -> bool:
    """
    Compile a CHILL source file to C

    Returns True on success, False on error
    """
    # Read input
    try:
        with open(input_path, 'r') as f:
            source = f.read()
    except IOError as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        return False

    # Parse
    if verbose:
        print(f"Parsing {input_path}...")

    try:
        program = parse(source, input_path)
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return False

    if verbose:
        print(f"  Modules: {len(program.modules)}")
        for mod in program.modules:
            print(f"    {mod.name}: {len(mod.procs)} procs, {len(mod.processes)} processes")

    # Semantic analysis
    if verbose:
        print("Analyzing...")

    errors = analyze(program)

    if errors:
        print(f"Semantic errors in {input_path}:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        if not check_only:
            print("Compilation aborted due to errors.", file=sys.stderr)
            return False

    if check_only:
        print(f"{input_path}: OK ({len(errors)} warnings)")
        return True

    # Generate C code
    if verbose:
        print("Generating C code...", file=sys.stderr)

    c_code = generate(program)

    # Write output
    if output_path is None or output_path == '-':
        # Output to stdout
        print(c_code)
    else:
        try:
            with open(output_path, 'w') as f:
                f.write(c_code)
        except IOError as e:
            print(f"Error writing {output_path}: {e}", file=sys.stderr)
            return False

        if verbose:
            print(f"Output written to {output_path}", file=sys.stderr)

        print(f"Compiled {input_path} -> {output_path}", file=sys.stderr)

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='CHILL to C Compiler',
        epilog='Based on ITU-T Z.200 (1999)'
    )

    parser.add_argument('input', nargs='?',
                       help='CHILL source file (.chl, .ch, .chill)')
    parser.add_argument('-o', '--output',
                       help='Output C file (default: input with .c extension)')
    parser.add_argument('-c', '--check', action='store_true',
                       help='Check syntax/semantics only, do not generate code')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--version', action='version',
                       version='CHILL Compiler 1.0.0')

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        sys.exit(1)

    success = compile_file(
        args.input,
        args.output,
        check_only=args.check,
        verbose=args.verbose
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
