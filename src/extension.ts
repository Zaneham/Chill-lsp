import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
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

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
