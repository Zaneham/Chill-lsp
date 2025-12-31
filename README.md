# CHILL Language Server

Language Server Protocol implementation for **CHILL** (CCITT High Level Language), the ITU-T programming language that has been quietly running the world's telephone networks since 1980.

When you pick up a phone and dial a number, there is a non-trivial probability that CHILL code is involved in making that connection happen. You've never heard of it. Neither has anyone else. The phones work anyway.

## What is CHILL?

**CHILL** was developed by the CCITT (now ITU-T) in the 1970s as a standardised programming language for telecommunications switching systems. The reasoning was sound: if every telephone company in the world was going to need software for their exchanges, perhaps they should all use the same language. This would promote interoperability, reduce training costs, and ensure a common standard.

It worked. CHILL became the dominant language for telephone switching software. Then everyone forgot about it.

### The Scale of Things

To understand CHILL's significance, consider the Siemens EWSD (Elektronisches WählSystem Digital):

- **200 million subscriber lines** across 105 countries
- **45 million lines of CHILL code** written by 1,600 engineers in Munich
- Software described as "predominantly written in CHILL"
- Still in service in telephone networks worldwide

When Siemens says "predominantly written in CHILL," they mean it. The entire call processing logic, billing systems, maintenance interfaces, and signalling protocols were implemented in CHILL. Every phone call through an EWSD switch is processed by CHILL code.

### Systems Running CHILL Code

| System | Manufacturer | Notes |
|--------|--------------|-------|
| **EWSD** | Siemens | 200 million lines in 105 countries |
| **System 12** | Alcatel/ITT | Major European deployment |
| **AXE-10** | Ericsson | Later versions, hybrid with PLEX |
| **5ESS** | AT&T/Lucent | Some components |
| **DMS** | Nortel | Interface modules |

Beyond telephone switches:

- **Deutsche Telekom** - Germany's national telephone infrastructure
- **Telenor** - Norway's telecommunications
- **Korea Telecom** - South Korea's telephone network
- **Telebras** - Brazil's telephone system
- **Railway signalling** - Various European rail networks
- **Air traffic control** - Some ATC communication systems

The language was discontinued from GCC in 2001 "due to lack of interest." The millions of telephone lines running on it were not consulted. The GCC maintainers, presumably, did not make many phone calls.

## A Brief History of Standardised Confusion

### The Committee Era (1970s)

In 1973, CCITT Study Group XI decided that telecommunications needed a standardised programming language. They formed a working group. The working group had meetings. Many meetings. Across multiple continents. For years.

The result was CHILL, first published as CCITT Recommendation Z.200 in 1980. It was a proper committee language: strongly typed, block structured, with features for concurrent programming and real-time systems. It had everything a telephone switch could need.

### The Revision Era (1980s-1990s)

| Year | Event | Notable Changes |
|------|-------|-----------------|
| 1980 | Z.200 First Edition | Initial specification |
| 1984 | Z.200 Second Edition | Bug fixes to the spec, essentially |
| 1988 | Z.200 Third Edition | Enhanced I/O, better exception handling |
| 1992 | Z.200 Fourth Edition | Module improvements |
| 1996 | Z.200 Fifth Edition | More module features |
| 1999 | Z.200 Sixth Edition | Object-oriented features (CHILL2000) |

Each revision was carefully deliberated by international committee. Each revision maintained backwards compatibility. Each revision was implemented by approximately three compiler vendors and ignored by everyone else.

### The Abandonment Era (2000s-Present)

In 2001, CHILL was removed from GCC. The commit message cited "lack of interest."

In 2024, Deutsche Telekom still runs EWSD switches. In 2025, someone made an IDE extension for it. The universe has a sense of humour.

## Features

### Code Intelligence
- **Completion:** Context-aware suggestions for keywords, modes, procedures, signals
- **Hover:** Type information and documentation for all symbols
- **Go to Definition:** Jump to DCL, NEWMODE, PROC, and PROCESS declarations
- **Find References:** Locate all uses of a symbol across the codebase
- **Document Symbols:** Outline view showing module structure

### Syntax Highlighting
- All 124 reserved words from ITU-T Z.200 Appendix III.1
- All 82 predefined names from Appendix III.2
- Comments (/* block */ and -- line)
- String and character literals
- Numeric literals including binary (B'101'), hex (H'FF'), and octal (O'77')
- CHILL2000 object-oriented keywords

### Semantic Analysis
- DCL (variable) declarations with mode tracking
- NEWMODE and SYNMODE (type) definitions
- PROC (procedure) signatures with parameter modes
- PROCESS (concurrent process) definitions
- SIGNAL definitions for inter-process communication
- MODULE structure and visibility (GRANT/SEIZE)

### CHILL to C Compiler

The extension includes a complete CHILL to C transpiler. Because sometimes understanding the code isn't enough—you need to run it on hardware that wasn't manufactured in 1985.

**Commands:**
| Command | Shortcut | Description |
|---------|----------|-------------|
| `CHILL: Compile to C` | `Ctrl+Shift+C` | Compile and show C in new panel |
| `CHILL: Compile to C (Save to File)` | — | Compile and save as `.c` file |

**Access:**
- Command palette (`Ctrl+Shift+P`)
- Right-click context menu in any CHILL file
- Editor title bar button
- Keyboard shortcut

**What it does:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  call_handler.chl                │  call_handler.c                  │
├─────────────────────────────────────────────────────────────────────┤
│  MODULE call_handler;            │  /* Generated by CHILL Compiler  │
│                                  │   * Source: ITU-T Z.200 (1999)   │
│  NEWMODE call_state = SET(       │   */                             │
│      idle, dial_tone,            │                                  │
│      connected);                 │  #include <pthread.h>            │
│                                  │                                  │
│  line_handler: PROCESS(id INT);  │  typedef enum {                  │
│      DCL state call_state;       │      idle, dial_tone, connected  │
│      ...                         │  } call_state;                   │
│  END line_handler;               │                                  │
│                                  │  void* line_handler(void* arg) { │
│  END call_handler;               │      ...                         │
│                                  │  }                               │
└─────────────────────────────────────────────────────────────────────┘
```

**Technical details:**
- Full ITU-T Z.200 (1999) parser with 124 keywords and 82 predefined names
- Semantic analysis with type checking and symbol resolution
- CHILL concurrency primitives map to pthreads:
  - `PROCESS` → `pthread_t` with wrapper functions
  - `SIGNAL` → Message queues with condition variables
  - `BUFFER` → Thread-safe bounded queues
  - `EVENT` → `pthread_cond_t` wrappers
  - `DELAY` → `nanosleep()`
- Generated C compiles with `gcc -lpthread`

**Use cases:**
- **Code understanding** - See what legacy CHILL actually does in readable C
- **Modernisation** - Port switch logic to modern Linux systems
- **Testing** - Run transpiled code on development machines
- **Training** - Learn CHILL semantics through C equivalents

The compiler won't route your phone calls. But it might help you understand the code that does.

## CHILL Language Overview

CHILL uses "modes" where other languages use "types." This is not merely different terminology; it reflects CHILL's philosophical commitment to being slightly confusing to anyone coming from another language.

### Basic Modes

| Mode | Description | Example |
|------|-------------|---------|
| `INT` | Integer | `DCL count INT;` |
| `BOOL` | Boolean | `DCL flag BOOL := TRUE;` |
| `CHAR` | Character | `DCL letter CHAR;` |
| `CHARS(n)` | Character string | `DCL name CHARS(30);` |
| `BOOLS(n)` | Bit string | `DCL flags BOOLS(8);` |
| `SET` | Enumeration | `NEWMODE state = SET(idle, busy, error);` |
| `RANGE` | Integer subrange | `NEWMODE byte = RANGE(0:255);` |
| `POWERSET` | Set of values | `NEWMODE options = POWERSET SET(a, b, c);` |
| `REF` | Reference/pointer | `DCL ptr REF INT;` |
| `STRUCT` | Structure/record | `NEWMODE point = STRUCT(x, y INT);` |
| `ARRAY` | Array | `DCL table ARRAY(1:100) INT;` |

### Concurrency Primitives

CHILL was designed for real-time telecommunications. Concurrency is not an afterthought; it is fundamental to the language.

| Construct | Purpose |
|-----------|---------|
| `PROCESS` | Define a concurrent process |
| `START` | Create a new process instance |
| `STOP` | Terminate a process |
| `SIGNAL` | Define inter-process signals |
| `SEND` | Send a signal to a process |
| `RECEIVE` | Wait for and receive a signal |
| `BUFFER` | Bounded queue for message passing |
| `EVENT` | Synchronisation primitive |
| `REGION` | Mutual exclusion section |
| `DELAY` | Time-based waiting |

When your phone call is being processed, multiple CHILL processes are coordinating through signals and buffers. The caller process. The callee process. The billing process. The maintenance process. The switch fabric controller. All written in a language nobody teaches anymore.

### Code Example

```chill
/*
 * Call Processing Module
 * Handles incoming calls on a subscriber line
 * This is what runs when you pick up your phone
 */

MODULE call_handler;

GRANT call_state, dial_tone, process_call;
SEIZE switch_fabric, billing, signalling;

-- Call states
NEWMODE call_state = SET(
    idle,           -- Waiting for activity
    dial_tone,      -- Subscriber has gone off-hook
    collecting,     -- Receiving dialed digits
    routing,        -- Finding a path through the switch
    alerting,       -- Ringing the destination
    connected,      -- Call in progress
    releasing       -- Tearing down the call
);

-- Subscriber line data
NEWMODE line_info = STRUCT(
    directory_num CHARS(15),
    current_state call_state,
    start_time TIME,
    destination CHARS(15)
);

-- Signals for inter-process communication
SIGNAL offhook_detected(line_id INT);
SIGNAL digit_received(line_id INT, digit INT);
SIGNAL answer_detected(line_id INT);
SIGNAL onhook_detected(line_id INT);

-- Process one subscriber line
line_handler: PROCESS(line_id INT);
    DCL info line_info;
    DCL digits CHARS(20) := '';

    info.current_state := idle;

    DO EVER;
        RECEIVE CASE
            (offhook_detected):
                IF info.current_state = idle THEN
                    apply_dial_tone(line_id);
                    info.current_state := dial_tone;
                    info.start_time := ABSTIME();
                FI;

            (digit_received IN digit):
                IF info.current_state = dial_tone THEN
                    remove_dial_tone(line_id);
                    info.current_state := collecting;
                FI;
                IF info.current_state = collecting THEN
                    digits := digits // CHAR(digit + 48);
                    IF LENGTH(digits) >= 10 THEN
                        -- Full number collected, route the call
                        info.destination := digits;
                        route_call(line_id, digits);
                        info.current_state := routing;
                    FI;
                FI;

            (answer_detected):
                IF info.current_state = alerting THEN
                    info.current_state := connected;
                    start_billing(line_id, info);
                FI;

            (onhook_detected):
                release_call(line_id);
                info.current_state := idle;
                digits := '';
        ESAC;
    OD;
END line_handler;

END call_handler;
```

This is a simplified example. Real EWSD code handles thousands of edge cases: busy signals, call waiting, call forwarding, emergency services, operator assistance, international routing, SS7 signalling, billing records, maintenance alarms, and the peculiar requirements of whatever national telephone authority has deployed the switch.

All in CHILL. All still running.

## Installation

### VS Code Extension

1. Install the extension from the VS Code marketplace (search "CHILL Language")
2. Ensure Python 3.8+ is installed
3. Open any `.chl`, `.chill`, or `.ch` file
4. Wonder why you're maintaining a telephone switch in 2025

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/Zaneham/chill-lsp

# Install dependencies
cd chill-lsp
npm install

# Compile TypeScript
npm run compile

# Package the extension
npx @vscode/vsce package

# Install in VS Code
code --install-extension chill-lsp-1.1.0.vsix
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `chill.pythonPath` | `python` | Path to Python interpreter |
| `chill.serverPath` | (bundled) | Path to custom LSP server |
| `chill.compilerPath` | (bundled) | Path to CHILL compiler directory |
| `chill.trace.server` | `off` | LSP communication tracing |

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.chl` | CHILL source file |
| `.chill` | CHILL source file (verbose) |
| `.ch` | CHILL source file (short form) |
| `.spc` | CHILL spec module |

## Documentation Sources

This LSP was built using official ITU-T documentation, which is remarkably comprehensive for a language nobody uses anymore:

### Standards

| Document | Description | Status |
|----------|-------------|--------|
| **ITU-T Z.200** | Official CHILL specification | Final revision 1999 |
| **ISO/IEC 9496** | Identical ISO standard | Mirrors Z.200 |

### Implementation Guides

| Document | Source | Notes |
|----------|--------|-------|
| **GNU CHILL Guide** | GCC 2.95.3 | Last version before removal |
| **CHILL2000 Tutorial** | Winkler | Object-oriented features |
| **CHILL History** | Rekdal, 1993 | Development history |
| **FSU Jena Archive** | University archive | Preserved documentation |

### Related Standards

CHILL was designed to work with other ITU-T telecommunications standards:

- **Z.100 (SDL)** - Specification and Description Language for protocol design
- **Z.120 (MSC)** - Message Sequence Charts for interaction modelling
- **Q.7xx** - SS7 signalling protocols (implemented in CHILL on many switches)

## The CHILL Philosophy

CHILL was designed with specific goals that reflect its telecommunications heritage:

1. **Strong typing** - The compiler catches errors before they cause trunk failures
2. **Compile-time checking** - Runtime errors in a telephone switch are expensive
3. **Built-in concurrency** - Telephone switches are inherently parallel systems
4. **Real-time primitives** - Calls must be processed within milliseconds
5. **Maintainability** - Switch software has a 20+ year lifecycle
6. **International standardisation** - Every PTT can use the same tools

These goals were largely achieved. The language works. The switches work. The phone network works. Nobody remembers the language exists.

## CHILL2000: Object-Oriented Telecommunications

The 1999 revision added object-oriented features, because it was 1999 and everything had to have objects. The features are actually quite sophisticated:

```chill
-- Abstract base mode for protocol handlers
NEWMODE protocol_handler = ABSTRACT MODULE
    DEFERRED handle_message: PROC(msg message) RETURNS(result);
    DEFERRED get_state: PROC() RETURNS(handler_state);
END;

-- Concrete implementation for SS7
NEWMODE ss7_handler = MODULE BASED_ON protocol_handler
    DCL state handler_state := idle;
    DCL buffer ARRAY(1:100) message;

    REIMPLEMENT handle_message: PROC(msg message) RETURNS(result);
        -- SS7 specific handling
    END;

    REIMPLEMENT get_state: PROC() RETURNS(handler_state);
        RETURN state;
    END;
END;
```

By the time these features were standardised, the telephone industry had largely stopped writing new CHILL code. The features exist. The documentation exists. The use cases may not.

## Why This Matters

Consider the situation:

- Millions of telephone lines are served by CHILL code
- The language was removed from the only open-source compiler 24 years ago
- The engineers who wrote EWSD are retiring or retired
- The Siemens documentation is proprietary
- Modern developers have never heard of CHILL
- The switches are still in service

Somewhere, a telecommunications engineer needs to modify call routing logic on an EWSD switch. They are probably using a text editor from 1995 because that's what was available when the switch was installed. They have no code completion, no hover documentation, no go-to-definition.

This LSP provides them with modern tooling. It won't solve the fundamental problem that their switch runs software in a language the world has forgotten, but at least they can navigate the codebase without memorising every DCL statement.

## Contributing

Contributions welcome, particularly:

- Syntax patterns from real-world CHILL code (EWSD, System 12, etc.)
- Improved semantic analysis
- Support for vendor-specific dialects
- Documentation corrections
- War stories from maintaining telephone switches

If you've maintained EWSD, System 12, or any other CHILL-based system, your knowledge would be invaluable. The language specification is available; the practical experience of using it is not.

## Known Limitations

- No type checking beyond basic mode inference
- Limited support for CHILL2000 object-oriented features
- No cross-module analysis (would require build system integration)
- Cannot actually route your phone calls (that's the switch's job)

## Licence

Apache License 2.0 - See LICENSE file for details.

Copyright 2025 Zane Hambly

## Related Projects

If programming telephone switches has left you wanting more vintage critical infrastructure computing:

- **[JOVIAL J73 LSP](https://github.com/Zaneham/jovial-lsp)** - For the language that flies F-15s, B-52s, and AWACS. Different infrastructure, same era. JOVIAL routes missiles; CHILL routes phone calls. Both still running. Both forgotten.

- **[CMS-2 LSP](https://github.com/Zaneham/cms2-lsp)** - The US Navy's tactical language. Powers Aegis cruisers and submarines. Naval telecommunications meets fire control.

- **[CORAL 66 LSP](https://github.com/Zaneham/coral66-lsp)** - The British Ministry of Defence's real-time language. Powers Tornado aircraft and Royal Navy systems. Commonwealth telecommunications.

- **[HAL/S LSP](https://github.com/Zaneham/hals-lsp)** - NASA's Space Shuttle language. Because someone had to do orbital telecommunications.

- **[IBM System/360 Languages](https://github.com/Zaneham/os360-lsp)** - COBOL F and PL/I F. The mainframes that the telephone switches talked to.

## Contact

Found a bug? Have EWSD source code you can share? Currently maintaining a telephone exchange in 2025 and wondering how this happened?

zanehambly@gmail.com

I'll respond faster than a call setup on a well-maintained EWSD. Though if your EWSD isn't well-maintained, that's a low bar.

## Acknowledgements

- **CCITT/ITU-T** for the language specification and 25 years of committee meetings
- **Siemens AG** for EWSD and proving 45 million lines of CHILL could work
- **Alcatel** for System 12 and the French perspective on switching
- **The FSU Jena CHILL archive** for preserving documentation nobody else kept
- **The 1,600 engineers in Munich** who wrote 45 million lines of CHILL and presumably needed a lot of coffee
- **The GCC developers** who maintained CHILL support until 2001
- **Everyone still maintaining CHILL code** in telephone switches, railway signalling, and other systems that the world has forgotten exist

---

*"The language was removed from GCC due to lack of interest. The phone network continues to function. These facts are unrelated."*

---

*"CHILL: Connecting the world's phone calls since 1980. Unknown to the world since approximately 1985."*

---

*"When you dial a number and it rings, CHILL is working. When you get a busy signal, CHILL is also working. When you get silence, that might be a bug. Please contact your local telecommunications provider, who will have no idea what you're talking about if you mention CHILL."*
