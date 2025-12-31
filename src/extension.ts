import * as path from 'path';
import * as vscode from 'vscode';
import { spawn } from 'child_process';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;
let outputChannel: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext) {
    // Create output channel for compiler
    outputChannel = vscode.window.createOutputChannel('CHILL Compiler');

    // Get configuration
    const config = vscode.workspace.getConfiguration('chill');
    const pythonPath = config.get<string>('pythonPath', 'python');
    let serverPath = config.get<string>('serverPath', '');

    // Use bundled server if not specified
    if (!serverPath) {
        serverPath = context.asAbsolutePath(
            path.join('chill_lsp_server.py')
        );
    }

    // Server options - run Python LSP server
    const serverOptions: ServerOptions = {
        command: pythonPath,
        args: [serverPath],
        transport: TransportKind.stdio
    };

    // Client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'chill' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{chl,chill,ch,spc}')
        }
    };

    // Create and start the client
    client = new LanguageClient(
        'chillLSP',
        'CHILL Language Server',
        serverOptions,
        clientOptions
    );

    // Start the client
    client.start();

    // Register compile command (show in panel)
    const compileCmd = vscode.commands.registerCommand('chill.compileToC', async () => {
        await compileCurrentFile(context, false);
    });
    context.subscriptions.push(compileCmd);

    // Register compile command (save to file)
    const compileSaveCmd = vscode.commands.registerCommand('chill.compileToCSave', async () => {
        await compileCurrentFile(context, true);
    });
    context.subscriptions.push(compileSaveCmd);

    // Register status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(phone) CHILL';
    statusBarItem.tooltip = 'CHILL Language Support (ITU-T Z.200) - Powering 200 million telephone lines';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Show welcome message
    vscode.window.showInformationMessage(
        'CHILL Language Server activated - Supporting EWSD, Alcatel System 12, and other telecom infrastructure'
    );
}

async function compileCurrentFile(context: vscode.ExtensionContext, saveToFile: boolean) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active CHILL file');
        return;
    }

    const document = editor.document;
    if (document.languageId !== 'chill') {
        vscode.window.showErrorMessage('Current file is not a CHILL file');
        return;
    }

    // Save the document first
    await document.save();

    const config = vscode.workspace.getConfiguration('chill');
    const pythonPath = config.get<string>('pythonPath', 'python');
    let compilerPath = config.get<string>('compilerPath', '');

    // Use bundled compiler if not specified
    if (!compilerPath) {
        compilerPath = context.asAbsolutePath(path.join('compiler'));
    }

    const inputFile = document.fileName;

    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine(`Compiling: ${inputFile}`);
    outputChannel.appendLine('─'.repeat(60));

    // Run the compiler
    const compilerScript = path.join(compilerPath, 'cli.py');
    const args = [compilerScript, inputFile];

    const process = spawn(pythonPath, args, {
        cwd: path.dirname(inputFile)
    });

    let stdout = '';
    let stderr = '';

    process.stdout.on('data', (data: Buffer) => {
        stdout += data.toString();
    });

    process.stderr.on('data', (data: Buffer) => {
        stderr += data.toString();
    });

    process.on('close', async (code: number) => {
        if (code !== 0) {
            outputChannel.appendLine('COMPILATION FAILED');
            outputChannel.appendLine('─'.repeat(60));
            outputChannel.appendLine(stderr || stdout);
            vscode.window.showErrorMessage('CHILL compilation failed - see output panel');
            return;
        }

        outputChannel.appendLine('COMPILATION SUCCESSFUL');
        outputChannel.appendLine('─'.repeat(60));

        if (saveToFile) {
            // Save to .c file alongside the source
            const outputFile = inputFile.replace(/\.(chl|chill|ch)$/i, '.c');
            const fs = await import('fs').then(m => m.promises);
            await fs.writeFile(outputFile, stdout);
            outputChannel.appendLine(`Output saved to: ${outputFile}`);
            vscode.window.showInformationMessage(`Compiled to ${path.basename(outputFile)}`);

            // Open the generated file
            const doc = await vscode.workspace.openTextDocument(outputFile);
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        } else {
            // Show in a new untitled document
            const doc = await vscode.workspace.openTextDocument({
                content: stdout,
                language: 'c'
            });
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        }
    });
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
