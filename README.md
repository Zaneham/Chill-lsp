# CHILL Language Server

Language Server Protocol implementation for **CHILL** (CCITT High Level Language), the ITU-T programming language that has been quietly running the world's telephone networks since 1980.

## What is CHILL?

**CHILL** was developed by the CCITT (now ITU-T) in the 1970s for programming telecommunications switching systems. When you make a phone call and it actually connects, there's a reasonable chance CHILL is involved somewhere in the chain.

### Systems Running CHILL Code

- **Siemens EWSD** - 200 million subscriber lines across 105 countries. The software is "predominantly written in CHILL."
- **Alcatel System 12** - Another major switching platform
- **Deutsche Telekom** - Germany's largest telephone company
- **Railway signalling** - Signal box programming in various countries
- **Legacy telecom switches** - Norway, Brazil, South Korea, and anywhere else EWSD was sold

The language was discontinued from GCC in 2001 "due to lack of interest." The 200 million phone lines running on it were not consulted.

## Features

### Code Intelligence
- **Completion:** Context-aware suggestions for keywords, modes, procedures
- **Hover:** Type information and documentation
- **Go to Definition:** Jump to DCL and NEWMODE declarations
- **Find References:** Find all uses of a symbol
- **Document Symbols:** Outline view of all declarations

### Syntax Highlighting
- Keywords and control flow
- Mode declarations (INT, BOOL, CHAR, STRUCT, etc.)
- Comments (/* */ and --)
- String literals
- Operators

## CHILL Language Overview

### Basic Types (Modes)

| Mode | Description | Example |
|------|-------------|---------|
| `INT` | Integer | `DCL count INT;` |
| `BOOL` | Boolean | `DCL flag BOOL;` |
| `CHAR` | Character | `DCL letter CHAR;` |
| `CHARS(n)` | Character string | `DCL name CHARS(30);` |
| `SET` | Enumeration | `NEWMODE state = SET(idle, busy, error);` |
| `RANGE` | Integer range | `NEWMODE byte = RANGE(0:255);` |
| `POWERSET` | Set of discrete values | `NEWMODE flags = POWERSET SET(a, b, c);` |
| `REF` | Reference/pointer | `DCL ptr REF INT;` |
| `STRUCT` | Structure | `NEWMODE point = STRUCT(x, y INT);` |
| `ARRAY` | Array | `DCL table ARRAY(1:100) INT;` |

### Key Constructs

```chill
/* This is a comment in CHILL */
-- This is also a comment

MODULE example;

/* Mode definitions */
NEWMODE counter = RANGE(0:65535);
NEWMODE status = SET(idle, active, error);

/* Synonym (constant) */
SYN max_size = 100;

/* Variable declarations */
DCL count counter := 0;
DCL state status := idle;
DCL buffer CHARS(256);

/* Procedure definition */
proc_name: PROC(input INT) RETURNS(INT);
  DCL result INT;
  result := input * 2;
  RETURN result;
END proc_name;

/* Process definition (concurrent) */
handler: PROCESS(id INT);
  DO WHILE TRUE;
    /* process logic */
  OD;
END handler;

/* Control structures */
IF count > 0 THEN
  count := count - 1;
ELSIF count = 0 THEN
  state := idle;
ELSE
  state := error;
FI;

CASE state OF
  (idle): /* handle idle */;
  (active): /* handle active */;
  (error): /* handle error */;
ESAC;

DO WHILE count > 0;
  count := count - 1;
OD;

DO FOR i := 1 TO max_size;
  /* loop body */
OD;

END example;
```

## Installation

### VS Code Extension

1. Install the extension from the VS Code marketplace
2. Ensure Python 3.8+ is installed
3. Open any `.chl`, `.chill`, or `.ch` file

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/Zaneham/chill-lsp

# Install dependencies
cd chill-lsp
npm install

# Compile TypeScript
npm run compile

# Install in VS Code
code --install-extension chill-lsp-1.0.0.vsix
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `chill.pythonPath` | `python` | Path to Python interpreter |
| `chill.serverPath` | (bundled) | Path to custom LSP server |
| `chill.trace.server` | `off` | LSP communication tracing |

## File Extensions

- `.chl` - CHILL source file
- `.chill` - CHILL source file (long form)
- `.ch` - CHILL source file (short form)
- `.spc` - CHILL spec module

## Documentation Sources

This LSP was built using official ITU-T documentation:

### Standards
| Document | Description | Year |
|----------|-------------|------|
| **ITU-T Z.200** | Official CHILL language specification | 1999 |
| **ISO/IEC 9496** | Identical ISO standard | 1999 |

### Tutorials and References
| Document | Description | Year |
|----------|-------------|------|
| **GNU CHILL Guide** | GCC 2.95.3 compiler documentation | 2001 |
| **CHILL2000 Tutorial** | Winkler's tutorial on CHILL2000 features | 2000 |
| **CHILL History** | Rekdal's paper on early CHILL history | 1993 |

## Language History

- **1970s:** CHILL developed by CCITT for telecom switching
- **1980:** First CCITT Recommendation Z.200 published
- **1984, 1988, 1992, 1996:** Language revisions
- **1999:** Final ITU-T Z.200 revision (CHILL2000)
- **2001:** Removed from GCC "due to lack of interest"
- **Present:** Still running in telecom infrastructure worldwide

## Why This Matters

The engineers who wrote EWSD are retiring. The Siemens documentation is proprietary. The language was dropped from GCC over two decades ago. Yet somewhere, right now, your phone call is being routed by CHILL code.

This LSP provides:
- Modern tooling for legacy code maintenance
- Documentation for a language the world has largely forgotten
- Support for the engineers keeping the phone network running

## Contributing

Contributions welcome, particularly:
- Syntax patterns from real-world CHILL code
- Improved semantic analysis
- Documentation corrections

If you've maintained EWSD or Alcatel System 12 and have insights about dialect variations, your knowledge would be invaluable.

## Licence

Apache License 2.0 - See LICENSE file for details.

Copyright 2025 Zane Hambly

## Related Projects

If programming telephone switches has left you wanting more vintage telecommunications computing:

- **[JOVIAL J73 LSP](https://github.com/Zaneham/jovial-lsp)** - For the language that flies F-15s and B-52s. Different infrastructure, same era. JOVIAL routes missiles; CHILL routes phone calls. Both still running.

- **[CMS-2 LSP](https://github.com/Zaneham/cms2-lsp)** - The US Navy's tactical language. Powers Aegis cruisers. Naval telecommunications, different continent.

- **[CORAL 66 LSP](https://github.com/Zaneham/coral66-lsp)** - The British Ministry of Defence's real-time language. Powers Tornado aircraft and Royal Navy vessels.

- **[IBM System/360 Languages](https://github.com/Zaneham/os360-lsp)** - COBOL F and PL/I F. Because telecom switches had to talk to mainframes eventually.

## Contact

Found a bug? Have EWSD source code you can share? Currently maintaining a telephone exchange and can't believe someone made IDE support for CHILL?

zanehambly@gmail.com

I'll answer your email faster than a switch routes a call. Probably. Depends on traffic.

## Acknowledgements

- CCITT/ITU-T for the language specification
- Siemens AG for making EWSD (and therefore proving CHILL worked)
- The FSU Jena CHILL archive for preserving documentation
- The 1,600 engineers in Munich who wrote 45 million lines of CHILL
- Everyone still maintaining telecom infrastructure that predates the web

---

*"The language was removed from GCC due to lack of interest. The phone network continues to function. These facts are unrelated."*
