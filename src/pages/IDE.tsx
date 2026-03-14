import { useState, useEffect, useRef, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Play, Trash2, Terminal, Loader2, Code2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { cpp } from '@codemirror/lang-cpp';
import { oneDark } from '@codemirror/theme-one-dark';
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import JSCPP from "JSCPP";

type Language = "python" | "javascript" | "cpp";

interface ExecutionResult {
  code: string;
  output: string;
  error?: string;
  timestamp: Date;
  language: Language;
}

const DEFAULT_CODE: Record<Language, string> = {
  python: "# Escreva seu código Python aqui\nprint('Hello, World!')\n\n# Experimente usar input:\n# nome = input('Digite seu nome: ')\n# print(f'Olá, {nome}!')",
  javascript: "// Escreva seu código JavaScript aqui\nconsole.log('Hello, World!');\n\n// Experimente usar prompt:\n// const nome = prompt('Digite seu nome: ');\n// console.log(`Olá, ${nome}!`);",
  cpp: "// C++ (em breve)\n// Suporte a C++ será adicionado em breve!\n#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello, World!\" << endl;\n    return 0;\n}",
};

const LANG_LABELS: Record<Language, string> = {
  python: "Python",
  javascript: "JavaScript",
  cpp: "C++",
};

export default function IDE() {
  const { toast } = useToast();
  const [language, setLanguage] = useState<Language>("python");
  const [codes, setCodes] = useState<Record<Language, string>>(DEFAULT_CODE);
  const [output, setOutput] = useState<string>("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [isPyodideReady, setIsPyodideReady] = useState(false);
  const [history, setHistory] = useState<ExecutionResult[]>([]);
  const pyodideRef = useRef<any>(null);

  const [isWaitingForInput, setIsWaitingForInput] = useState(false);
  const [currentInputValue, setCurrentInputValue] = useState("");
  const inputResolveRef = useRef<((value: string) => void) | null>(null);

  const code = codes[language];
  const setCode = (val: string) => setCodes(prev => ({ ...prev, [language]: val }));

  const editorExtensions = useMemo(() => {
    switch (language) {
      case "python": return [python()];
      case "javascript": return [javascript()];
      case "cpp": return [cpp()];
    }
  }, [language]);

  const isReady = language === "python" ? isPyodideReady : true;
  const statusLabel = language === "python"
    ? (isPyodideReady ? "Python Pronto" : "Carregando Python...")
    : language === "javascript"
      ? "JavaScript Pronto"
      : "C++ Pronto";

  // Inicializar Pyodide
  useEffect(() => {
    const loadPyodide = async () => {
      try {
        // @ts-ignore
        const pyodide = await window.loadPyodide({
          indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",
        });
        await pyodide.runPythonAsync(`
          import sys
          from io import StringIO
          sys.stdout = StringIO()
        `);
        pyodideRef.current = pyodide;
        setIsPyodideReady(true);
        toast({ title: "Python pronto!", description: "Ambiente Python carregado e pronto para uso" });
      } catch (error) {
        toast({
          title: "Erro ao carregar Python",
          description: error instanceof Error ? error.message : "Não foi possível carregar o ambiente Python",
          variant: "destructive",
        });
      }
    };
    loadPyodide();
  }, [toast]);

  // Python input handler
  const handleInput = (prompt: string): Promise<string> => {
    return new Promise((resolve) => {
      setOutput(prev => prev + prompt);
      setIsWaitingForInput(true);
      setCurrentInputValue("");
      inputResolveRef.current = resolve;
    });
  };

  const handleConsoleSubmit = (value: string) => {
    if (inputResolveRef.current) {
      setOutput(prev => prev + value + "\n");
      inputResolveRef.current(value);
      inputResolveRef.current = null;
      setIsWaitingForInput(false);
      setCurrentInputValue("");
    }
  };

  // Execute Python
  const executePython = async () => {
    if (!isPyodideReady || !pyodideRef.current) return;
    const pyodide = pyodideRef.current;

    await pyodide.runPythonAsync(`sys.stdout = StringIO()`);
    pyodide.globals.set("js_input", handleInput);

    await pyodide.runPythonAsync(`
import builtins
import js

async def custom_input(prompt=''):
    result = await js_input(prompt)
    return result

builtins.input = custom_input
`);

    const processedCode = code.replace(/(\s*)(\w+\s*=\s*)?input\(/g, '$1$2await input(');
    const lines = processedCode.split('\n').map(line => '    ' + line);
    const wrappedCode = 'async def __user_code__():\n' + lines.join('\n') + '\n\nawait __user_code__()';

    await pyodide.runPythonAsync(wrappedCode);

    const stdout = await pyodide.runPythonAsync(`sys.stdout.getvalue()`);
    return stdout || "Código executado com sucesso (sem output)";
  };

  // Execute JavaScript
  const executeJavaScript = async () => {
    const logs: string[] = [];

    // Create a sandboxed console
    const sandboxConsole = {
      log: (...args: any[]) => logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' ')),
      error: (...args: any[]) => logs.push('ERROR: ' + args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' ')),
      warn: (...args: any[]) => logs.push('WARN: ' + args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' ')),
      info: (...args: any[]) => logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' ')),
      table: (data: any) => logs.push(JSON.stringify(data, null, 2)),
      clear: () => { logs.length = 0; },
      dir: (obj: any) => logs.push(JSON.stringify(obj, null, 2)),
    };

    // prompt() replacement that uses our input system
    const sandboxPrompt = (msg: string = '') => {
      // For simplicity, prompt is synchronous in JS — we use window.prompt as fallback
      return window.prompt(msg) || '';
    };

    const sandboxAlert = (msg: string = '') => {
      logs.push(`[alert] ${msg}`);
    };

    // Build and execute function
    const fn = new Function('console', 'prompt', 'alert', code);
    fn(sandboxConsole, sandboxPrompt, sandboxAlert);

    return logs.length > 0 ? logs.join('\n') : "Código executado com sucesso (sem output)";
  };

  // Execute C++
  const executeCpp = async () => {
    const outputBuffer: string[] = [];
    
    const config = {
      stdio: {
        write: (s: string) => {
          outputBuffer.push(s);
        },
      },
      unsigned_overflow: "warn" as const,
    };

    const exitCode = JSCPP.run(code, "", config);
    const result = outputBuffer.join('');
    
    if (result) {
      return result + `\n[Processo finalizado com código ${exitCode}]`;
    }
    return `Código executado com sucesso (código de saída: ${exitCode})`;
  };

  // Main execute
  const executeCode = async () => {
    if (!code.trim() || !isReady) return;

    setIsExecuting(true);
    setOutput("");

    try {
      let result: string;

      if (language === "python") {
        result = await executePython();
      } else if (language === "javascript") {
        result = await executeJavaScript();
      } else {
        result = await executeCpp();
      }

      setOutput(result);
      setHistory(prev => [{ code, output: result, timestamp: new Date(), language }, ...prev].slice(0, 10));
      toast({ title: "Executado com sucesso", description: `Código ${LANG_LABELS[language]} executado` });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Erro desconhecido";
      setOutput(`Erro: ${errorMessage}`);
      setHistory(prev => [{ code, output: "", error: errorMessage, timestamp: new Date(), language }, ...prev].slice(0, 10));
      toast({ title: "Erro de execução", description: errorMessage, variant: "destructive" });
    } finally {
      setIsExecuting(false);
    }
  };

  const clearConsole = () => setOutput("");
  const clearHistory = () => {
    setHistory([]);
    toast({ title: "Histórico limpo", description: "Todas as execuções anteriores foram removidas" });
  };

  const handleLanguageChange = (val: string) => {
    if (val === "python" || val === "javascript" || val === "cpp") {
      setLanguage(val);
      setOutput("");
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold flex items-center gap-3">
            <Code2 className="h-9 w-9" />
            IDE Online
          </h1>
          <p className="text-muted-foreground mt-2">
            Execute código diretamente no navegador
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <Tabs value={language} onValueChange={handleLanguageChange}>
            <TabsList>
              <TabsTrigger value="python" className="gap-1.5">
                🐍 Python
              </TabsTrigger>
              <TabsTrigger value="javascript" className="gap-1.5">
                ⚡ JavaScript
              </TabsTrigger>
              <TabsTrigger value="cpp" className="gap-1.5">
                ⚙️ C++
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Status indicator */}
          {isReady ? (
            <div className="flex items-center gap-2 text-green-600">
              <Terminal className="h-5 w-5" />
              <span className="font-medium text-sm">{statusLabel}</span>
            </div>
          ) : language === "cpp" ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="text-sm">{statusLabel}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">{statusLabel}</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Editor */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Editor de Código</CardTitle>
            <CardDescription>Escreva seu código {LANG_LABELS[language]} aqui</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border rounded-lg overflow-hidden">
              <CodeMirror
                value={code}
                height="400px"
                theme={oneDark}
                extensions={editorExtensions}
                onChange={(value) => setCode(value)}
                className="text-base"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={executeCode}
                disabled={!isReady || isExecuting}
                className="flex-1"
              >
                {isExecuting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Executando...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Executar Código
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={clearConsole}>
                <Trash2 className="mr-2 h-4 w-4" />
                Limpar Console
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Console */}
        <Card>
          <CardHeader>
            <CardTitle>Console</CardTitle>
            <CardDescription>Saída da execução</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[360px] w-full rounded-md border bg-black/90 p-4">
              <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                {output || "Aguardando execução..."}
                {isWaitingForInput && <span className="animate-pulse">_</span>}
              </pre>
            </ScrollArea>
            <div className="mt-2">
              {isWaitingForInput ? (
                <Input
                  value={currentInputValue}
                  onChange={(e) => setCurrentInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleConsoleSubmit(e.currentTarget.value);
                    }
                  }}
                  placeholder="Digite sua entrada e pressione Enter..."
                  autoFocus
                  className="bg-black/90 text-green-400 border-green-700 font-mono placeholder:text-gray-600"
                />
              ) : (
                <div className="h-[40px]" />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Histórico */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Histórico de Execuções</CardTitle>
            <CardDescription>Últimas 10 execuções de código</CardDescription>
          </div>
          {history.length > 0 && (
            <Button variant="outline" size="sm" onClick={clearHistory}>
              <Trash2 className="mr-2 h-4 w-4" />
              Limpar Histórico
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Nenhuma execução ainda. Execute um código para ver o histórico.
            </p>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-4">
                {history.map((item, index) => (
                  <Card key={index} className={item.error ? "border-destructive" : ""}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm flex items-center gap-2">
                          Execução #{history.length - index}
                          <Badge variant="outline" className="text-[10px]">
                            {LANG_LABELS[item.language]}
                          </Badge>
                        </CardTitle>
                        <span className="text-xs text-muted-foreground">
                          {item.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Código:</p>
                        <div className="border rounded-md overflow-hidden">
                          <CodeMirror
                            value={item.code}
                            height="auto"
                            maxHeight="150px"
                            theme={oneDark}
                            extensions={item.language === "python" ? [python()] : item.language === "javascript" ? [javascript()] : [cpp()]}
                            editable={false}
                            basicSetup={{ lineNumbers: false, foldGutter: false }}
                          />
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">
                          {item.error ? "Erro:" : "Saída:"}
                        </p>
                        <pre className={`text-xs p-2 rounded-md border font-mono whitespace-pre-wrap ${item.error ? "bg-destructive/10 text-destructive" : "bg-muted"}`}>
                          {item.error || item.output}
                        </pre>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
